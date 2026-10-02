#!/usr/bin/env python3
"""Private Atria stream transport with distinct preferred credential slots.

No caller-supplied URL, credential, model or slot. Existing configured deployments
only. Failover is bounded; per-credential Retry-After cooldown is respected.
"""
from functools import lru_cache
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
TOTAL_SECONDS = 600
IDLE_SECONDS = 90
lock = threading.Lock()
cooldowns = {}

class StreamStartTimeout(TimeoutError):
    pass
class StreamIdleTimeout(TimeoutError):
    pass
class StreamIncomplete(ValueError):
    pass
class PoolUnavailable(ValueError):
    pass
class TransportConfigurationError(ValueError):
    def __init__(self, code, slot=None):
        self.code, self.slot = code, slot
        super().__init__(code)

def safe_reason(exc):
    if isinstance(exc, TransportConfigurationError):
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
    return {'code': known.get(str(exc), type(exc).__name__), 'slot': None}

REASON_AR = {
    'endpoint_mismatch': 'عنوان اتصال المراجعين لا يطابق عنوان المزوّد المعتمد',
    'model_mismatch': 'اسم النموذج في اتصال المراجعين غير مطابق',
    'credential_missing': 'مفتاح أحد المراجعين غير موجود',
    'credential_invalid_format': 'صيغة مفتاح أحد المراجعين تحتوي أحرفًا غير صالحة؛ لا حاجة لعرض قيمته',
    'no_review_credentials': 'لا توجد مفاتيح مهيأة للمراجعين',
    'invalid_http_header': 'تعذر إرسال ترويسة الاتصال بسبب قيمة غير صالحة',
    'model_answer_empty_or_oversized': 'رد النموذج فارغ أو أكبر من حد الرد الداخلي',
    'stream_incomplete': 'وصل رد مقطوع ولم تصل علامة اكتماله',
    'no_final_answer': 'لم يصل نص جواب نهائي',
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

def collect_sse(response, clock=time.monotonic):
    start=clock(); total=0; pieces=[]; terminal=False; finish=None; saw_event=False
    while True:
        if clock()-start > TOTAL_SECONDS:
            raise StreamIdleTimeout('Stream exceeded its bounded duration')
        try:
            raw=response.readline(LIMIT+1)
        except (TimeoutError, OSError) as exc:
            raise (StreamIdleTimeout if saw_event else StreamStartTimeout)('Response stream stopped') from None
        total += len(raw)
        if total > LIMIT:
            raise StreamIncomplete('Stream exceeds its size limit')
        if not raw:
            break
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
        text=delta.get('content')
        if isinstance(text,str):
            pieces.append(text)
        finish=choice.get('finish_reason') or finish
    if not terminal and finish not in ('stop','length'):
        raise StreamIncomplete('No completion marker; partial text is not a finished review')
    text=''.join(pieces).strip()
    text=clean_answer(text)
    if not text or finish in ('content_filter','tool_calls'):
        raise StreamIncomplete('No supported final answer')
    if finish=='length':
        text += '\n[الرد محدود بسقف الإخراج؛ يجب عدم اعتبار التفاصيل الناقصة محسومة.]'
    return text

def stream(route, system, user, opener=None):
    opener=opener or build_opener(NoRedirect)
    request=Request(route['base']+'/chat/completions', method='POST',
        headers={'Authorization':'Bearer '+route['key'],'Content-Type':'application/json','Accept':'text/event-stream'},
        data=json.dumps({'model':route['model'],'messages':[{'role':'system','content':system},{'role':'user','content':user}],
                         'max_tokens':6144,'stream':True},ensure_ascii=False).encode())
    try:
        response=opener.open(request,timeout=IDLE_SECONDS)
    except ValueError:
        raise TransportConfigurationError('invalid_http_header') from None
    except (TimeoutError, URLError) as exc:
        if isinstance(exc, TimeoutError) or isinstance(getattr(exc,'reason',None),TimeoutError):
            raise StreamStartTimeout('No initial response') from None
        raise
    with response:
        content_type=response.headers.get('Content-Type','').lower()
        if 'application/json' in content_type:
            # A compatible endpoint may return JSON despite stream=true.
            payload=response.read(LIMIT+1)
            if len(payload)>LIMIT:
                raise StreamIncomplete('JSON response exceeds limit')
            parsed=json.loads(payload); choice=parsed['choices'][0]
            text=choice['message'].get('content')
            if choice.get('finish_reason') not in ('stop','length') or not isinstance(text,str) or not text.strip():
                raise StreamIncomplete('JSON response is incomplete')
            text=clean_answer(text)
            if not text:
                raise StreamIncomplete('Only private reasoning was returned')
            return text
        return collect_sse(response)

def model_call(system, user, slot=0, pool=None, requester=stream, clock=time.monotonic):
    pool=routes() if pool is None else pool
    errors=[]
    for index in candidates(slot,len(pool)):
        with lock:
            if cooldowns.get(index,0)>clock():
                continue
        if len(errors)>=3:
            break
        try:
            return requester(pool[index],system,user)
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
