#!/usr/bin/env python3
"""Private Atria stream transport with distinct preferred credential slots.

No caller-supplied URL, credential, model or slot. Existing configured deployments
only. Failover is bounded; per-credential Retry-After cooldown is respected.
"""
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import json
import os
import re
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener
from agent_repo_read import NoRedirect

LIMIT = 2 * 1024 * 1024
TOTAL_SECONDS = 5400
IDLE_SECONDS = 300
# Atria supports integer generation limits through 65,536; reserve enough room
# for a complete answer while keeping generation explicitly bounded.
REVIEW_OUTPUT_TOKENS = 16384
lock = threading.Lock()
cooldowns = {}

class ReviewDeadlineExceeded(TimeoutError):
    pass

def check_deadline(deadline, clock=time.monotonic):
    if deadline is not None and clock() >= deadline:
        raise ReviewDeadlineExceeded()

class StreamStartTimeout(TimeoutError):
    pass
class StreamIdleTimeout(TimeoutError):
    pass
class StreamIncomplete(ValueError):
    pass
class FinalAnswerError(StreamIncomplete):
    def __init__(self, code, slot=None):
        self.code, self.slot = code, slot
        super().__init__(code)

class PoolUnavailable(ValueError):
    pass
class TransportConfigurationError(ValueError):
    def __init__(self, code, slot=None):
        self.code, self.slot = code, slot
        super().__init__(code)

def safe_reason(exc):
    if type(exc).__name__=='LeaderContractError':return {'code':exc.code,'slot':None}
    if isinstance(exc, (TransportConfigurationError, FinalAnswerError)):
        return {'code': exc.code, 'slot': exc.slot}
    known = {
        'Model response is empty or exceeds its limit': 'model_answer_empty_or_oversized',
        'Direct review transport requires the configured Atria endpoint': 'endpoint_mismatch',
        'Direct review transport requires the configured Atria model': 'model_mismatch',
        'Review credential is unavailable': 'credential_missing',
        'No configured review credentials': 'no_review_credentials',
        'No completion marker; partial text is not a finished review': 'stream_incomplete',
        'No supported final answer': 'no_final_answer',
        'Stream exceeds its size limit': 'stream_size_limit',
        'Only private reasoning was returned': 'only_reasoning_no_answer',
    }
    if type(exc).__name__ == 'DeliberationContractError':
        return {'code':'deliberation_invalid_response','slot':None}
    return {'code': known.get(str(exc), type(exc).__name__), 'slot': None}

REASON_AR = {
    'three_probe_credentials_missing': 'لا توجد ثلاثة مفاتيح مختلفة لبدء الفحص المقارن',
    'ReviewDeadlineExceeded': 'بلغ الطلب الحد الأقصى للمدة المسموح بها',
    'deliberation_invalid_response': 'لم يصل اقتراح أو تصويت صالح؛ لا يمكن اعتماد اتفاق جماعي',
    'endpoint_mismatch': 'عنوان اتصال المراجعين لا يطابق عنوان المزوّد المعتمد',
    'model_mismatch': 'اسم النموذج في اتصال المراجعين غير مطابق',
    'credential_missing': 'مفتاح أحد المراجعين غير موجود',
    'credential_invalid_format': 'صيغة مفتاح أحد المراجعين تحتوي أحرفًا غير صالحة؛ لا حاجة لعرض قيمته',
    'no_review_credentials': 'لا توجد مفاتيح مهيأة للمراجعين',
    'invalid_http_header': 'تعذر إرسال ترويسة الاتصال بسبب قيمة غير صالحة',
    'model_answer_empty_or_oversized': 'رد النموذج فارغ أو أكبر من حد الرد الداخلي',
    'stream_incomplete': 'وصل رد مقطوع ولم تصل علامة اكتماله',
    'no_final_answer': 'لم يصل نص جواب نهائي',
    'empty_final_answer': 'انتهى رد المزوّد دون نص جواب نهائي',
    'reasoning_without_final_answer': 'وصل تفكير داخلي فقط دون جواب نهائي',
    'output_limit_reached': 'بلغ رد المزوّد سقف الإخراج؛ لا يمكن اعتماد الرد المبتور',
    'response_filtered': 'حجب المزوّد الرد',
    'unsupported_tool_answer': 'أعاد المزوّد طلب أداة بدل جواب المراجع',
    'response_refused': 'أعاد المزوّد رفضًا بدل جواب المراجع',
    'only_reasoning_no_answer': 'وصل تفكير داخلي دون جواب نهائي',
    'StreamStartTimeout': 'لم يبدأ المزوّد إرسال الرد ضمن المهلة',
    'StreamIdleTimeout': 'توقف وصول أجزاء الرد ضمن المهلة',
}

@lru_cache(maxsize=1)
def routes():
    import yaml
    with open(os.environ['NOVA_COUNCIL_ROUTE_FILE'], encoding='utf-8') as handle:
        return configured_routes(yaml.safe_load(handle), os.environ)

def configured_routes(config, env):
    result=[]; seen=set()
    alias=env.get('AGENT_MODEL','opencrabs-model')
    for slot, item in enumerate(config['model_list'], 1):
        if item.get('model_name') != alias:
            continue
        p=item['litellm_params']; base=p.get('api_base','').rstrip('/')
        url=urlparse(base)
        # This direct transport is intentionally specific to the existing Atria service.
        if url.scheme!='https' or url.hostname!='api.atria-asi.ai' or url.path!='/v1' or url.username or url.password or url.query or url.fragment or url.port not in (None,443):
            raise TransportConfigurationError('endpoint_mismatch',slot)
        model=p.get('model','')
        if model!='openai/Atria-Dawn-Preview':
            raise TransportConfigurationError('model_mismatch',slot)
        key=p.get('api_key','')
        if isinstance(key, str) and key.startswith('os.environ/'):
            key=env.get(key.removeprefix('os.environ/'),'')
        if not isinstance(key, str) or not key.strip():
            raise TransportConfigurationError('credential_missing',slot)
        key=key.strip()
        if any(ch.isspace() or ord(ch)<33 or ord(ch)>126 for ch in key):
            raise TransportConfigurationError('credential_invalid_format',slot)
        if key not in seen:
            seen.add(key); result.append({'base':base,'model':'Atria-Dawn-Preview','key':key})
    if not result:
        raise ValueError('No configured review credentials')
    return result

def candidates(slot, count):
    preferred=slot % count
    # Slots 1..5: reviewers, cross-review, synthesis. Slots 6..10: first reserves.
    return list(dict.fromkeys([preferred]+list(range(5,count))+list(range(count))))

def clean_answer(text):
    text=re.sub(r'<(think|thinking|analysis|reasoning)>.*?</\1>', '', text, flags=re.S|re.I).strip()
    return re.sub(r'<(?:think|thinking|analysis|reasoning)>.*$', '', text, flags=re.S|re.I).strip()

def final_content(value):
    if isinstance(value,str):
        return value
    if isinstance(value,list):
        return ''.join(part['text'] for part in value if isinstance(part,dict)
                       and part.get('type')=='text' and isinstance(part.get('text'),str))
    return ''

def validate_final(text, finish, had_reasoning=False, refused=False):
    if finish=='length':
        raise FinalAnswerError('output_limit_reached')
    if finish=='content_filter':
        raise FinalAnswerError('response_filtered')
    if finish in ('tool_calls','function_call'):
        raise FinalAnswerError('unsupported_tool_answer')
    if refused:
        raise FinalAnswerError('response_refused')
    cleaned=clean_answer(text)
    if not cleaned:
        raise FinalAnswerError('reasoning_without_final_answer' if had_reasoning or text.strip() else 'empty_final_answer')
    return cleaned

def collect_sse(response, clock=time.monotonic, deadline=None, activity=None):
    start=clock(); total=0; pieces=[]; terminal=False; finish=None; saw_event=False; had_reasoning=False; refused=False
    last_progress=start
    while True:
        check_deadline(deadline,clock)
        if clock()-start > TOTAL_SECONDS:
            raise StreamIdleTimeout('Stream exceeded its bounded duration')
        if clock()-last_progress > IDLE_SECONDS:
            raise (StreamIdleTimeout if saw_event else StreamStartTimeout)('No meaningful stream progress')
        try:
            raw=response.readline(LIMIT+1)
        except (TimeoutError, OSError) as exc:
            check_deadline(deadline,clock)
            raise (StreamIdleTimeout if saw_event else StreamStartTimeout)('Response stream stopped') from None
        total += len(raw)
        if total > LIMIT:
            raise StreamIncomplete('Stream exceeds its size limit')
        if not raw:
            break
        if clock()-last_progress > IDLE_SECONDS:
            raise (StreamIdleTimeout if saw_event else StreamStartTimeout)('No meaningful stream progress')
        line=raw.decode('utf-8').strip()
        if not line.startswith('data:'):
            continue
        data=line[5:].strip()
        if data=='[DONE]':
            terminal=True; break
        if not data:
            continue
        event=json.loads(data); saw_event=True
        if event.get('error'):
            raise StreamIncomplete('Provider reported a stream error')
        choices=event.get('choices',[])
        if not choices:
            continue
        choice=choices[0]; delta=choice.get('delta',{})
        if delta.get('tool_calls'):
            raise StreamIncomplete('A reviewer attempted an unsupported tool call')
        # Do not emit reasoning_content/thinking/private deliberation.
        had_reasoning = had_reasoning or bool(delta.get('reasoning_content') or delta.get('reasoning') or delta.get('thinking'))
        refused = refused or bool(delta.get('refusal'))
        text=final_content(delta.get('content'))
        # Reasoning deltas count as activity without retaining or emitting their text.
        if text or delta.get('reasoning_content') or delta.get('reasoning') or delta.get('thinking') or choice.get('finish_reason'):
            last_progress=clock()
            if activity:activity()
        if text:
            pieces.append(text)
        finish=choice.get('finish_reason') or finish
    check_deadline(deadline,clock)
    if not terminal and finish not in ('stop','length'):
        raise StreamIncomplete('No completion marker; partial text is not a finished review')
    return validate_final(''.join(pieces),finish,had_reasoning,refused)

def stream(route, system, user, opener=None, max_tokens=REVIEW_OUTPUT_TOKENS, deadline=None, activity=None):
    check_deadline(deadline)
    opener=opener or build_opener(NoRedirect)
    request=Request(route['base']+'/chat/completions', method='POST',
        headers={'Authorization':'Bearer '+route['key'],'Content-Type':'application/json','Accept':'text/event-stream'},
        data=json.dumps({'model':route['model'],'messages':[{'role':'system','content':system},{'role':'user','content':user}],
                         'max_tokens':max_tokens,'stream':True},ensure_ascii=False).encode())
    try:
        response=opener.open(request,timeout=IDLE_SECONDS if deadline is None else min(IDLE_SECONDS,max(0.001,deadline-time.monotonic())))
    except ValueError:
        raise TransportConfigurationError('invalid_http_header') from None
    except (TimeoutError, URLError) as exc:
        check_deadline(deadline)
        if isinstance(exc, TimeoutError) or isinstance(getattr(exc,'reason',None),TimeoutError):
            raise StreamStartTimeout('No initial response') from None
        raise
    with response:
        content_type=response.headers.get('Content-Type','').lower()
        if 'application/json' in content_type:
            # A compatible endpoint may return JSON despite stream=true.
            payload=response.read(LIMIT+1)
            check_deadline(deadline)
            if len(payload)>LIMIT:
                raise StreamIncomplete('JSON response exceeds limit')
            parsed=json.loads(payload); choice=parsed['choices'][0]
            message=choice['message']; finish=choice.get('finish_reason')
            if finish not in ('stop','length','content_filter','tool_calls','function_call'):
                raise StreamIncomplete('JSON response is incomplete')
            return validate_final(final_content(message.get('content')),finish,
                                  bool(message.get('reasoning_content') or message.get('reasoning') or message.get('thinking')),
                                  bool(message.get('refusal')))
        return collect_sse(response,deadline=deadline,activity=activity)

def model_call(system, user, slot=0, pool=None, requester=stream, clock=time.monotonic, deadline=None, observer=None):
    pool=routes() if pool is None else pool
    errors=[]
    for index in candidates(slot,len(pool)):
        check_deadline(deadline,clock)
        with lock:
            if cooldowns.get(index,0)>clock():
                continue
        if len(errors)>=3:
            break
        try:
            started=clock(); outcome='failed'; reason=None
            last_notice=started-15
            def activity():
                nonlocal last_notice
                if observer is not None and clock()-last_notice>=15:
                    last_notice=clock()
                    observer({'kind':'activity','credential_slot':index+1,
                              'elapsed_seconds':round(max(0,clock()-started),2)})
            try:
                result=requester(pool[index],system,user,deadline=deadline,activity=activity) if requester is stream else requester(pool[index],system,user)
                check_deadline(deadline,clock)
                outcome='completed'
                return result
            except Exception as exc:
                reason=safe_reason(exc)['code']
                raise
            finally:
                if observer is not None:
                    observer({'credential_slot':index+1,'elapsed_seconds':round(max(0,clock()-started),2),
                              'outcome':outcome,'reason_code':reason})
        except HTTPError as exc:
            if exc.code not in (401,403,408,429,500,502,503,504):
                raise
            try:
                delay=float(exc.headers.get('Retry-After','60'))
            except (TypeError, ValueError):
                delay=60
            with lock:
                cooldowns[index]=clock()+max(60,delay)
            errors.append(exc)
        except FinalAnswerError as exc:
            exc.slot=index+1
            # Only empty/reasoning-only responses rotate; never evade a refusal or filter.
            if exc.code not in ('empty_final_answer','reasoning_without_final_answer'):
                raise
            with lock:
                cooldowns[index]=clock()+60
            errors.append(exc)
        except (StreamStartTimeout,StreamIdleTimeout,URLError) as exc:
            with lock:
                cooldowns[index]=clock()+60
            errors.append(exc)
    if errors:
        raise errors[-1]
    raise PoolUnavailable('All configured review credentials are cooling down')


def diagnostics():
    """Local validation only: no API calls, credentials, fingerprints or quota claims."""
    try:
        pool=routes()
        return {'configuration_valid':True, 'unique_credentials':len(pool),
                'distinct_reviewer_preferences':len(pool)>=3,
                'api_requests_made':0, 'provider_acceptance_verified':False,
                'message':'الإعداد المحلي صالح. قبول المفاتيح من المزوّد لم يُختبر بهذا الفحص.'}
    except Exception as exc:
        reason=safe_reason(exc)
        return {'configuration_valid':False, 'api_requests_made':0,
                'provider_acceptance_verified':False, 'reason_code':reason['code'],
                'slot':reason['slot'], 'message':REASON_AR.get(reason['code'],'تعذر فحص الإعداد المحلي؛ لم تُعرض أي مفاتيح.')}


def probe_connection():
    # Exactly one small request with the first configured unique credential.
    # No fallback: success never masquerades as verification of a different key.
    pool=routes()
    stream(pool[0], 'This is a connection check. Reply with one short word only.',
           'Reply: READY', max_tokens=512)
    return {'credential_slot':1, 'api_requests':1, 'complete_response':True}


def probe_reviewers(pool=None, requester=stream, clock=time.monotonic, observer=None):
    """Exactly three identical tiny requests, distinct first slots, no sources/fallback."""
    pool=routes() if pool is None else pool
    if len(pool)<3:
        raise TransportConfigurationError('three_probe_credentials_missing')
    deadline=clock()+180
    def check(index):
        started=clock(); outcome='failed'; reason=None
        try:
            check_deadline(deadline,clock)
            requester(pool[index], 'This is a connection check. Reply with one short word only.',
                      'Reply: READY',max_tokens=512,deadline=deadline)
            check_deadline(deadline,clock)
            outcome='completed'
        except Exception as exc:
            reason=safe_reason(exc)['code']
        event={'credential_slot':index+1,'elapsed_seconds':round(max(0,clock()-started),2),
               'outcome':outcome,'reason_code':reason}
        if observer is not None:observer(event)
        return event
    with ThreadPoolExecutor(max_workers=3) as executor:
        results=list(executor.map(check,range(3)))
    return {'api_requests':3,'completed_requests':sum(r['outcome']=='completed' for r in results),
            'results':results,'scope':'first_three_credentials_only'}
