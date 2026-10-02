#!/usr/bin/env python3
"""Bounded repeated deliberation: unanimity is validated, never inferred from prose."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json

MAX_ROUNDS=3
MAX_REQUESTS=16

class DeliberationContractError(ValueError):
    pass

def object_response(text):
    if not isinstance(text,str) or len(text)>30000:
        raise DeliberationContractError('Invalid structured deliberation response')
    text=text.strip()
    if text.startswith('```') and text.endswith('```'):
        text='\n'.join(text.splitlines()[1:-1]).strip()
    try:
        value=json.loads(text)
    except json.JSONDecodeError:
        raise DeliberationContractError('Deliberation response was not valid JSON') from None
    if not isinstance(value,dict):
        raise DeliberationContractError('Deliberation response must be an object')
    return value

def proposal_response(text):
    value=object_response(text)
    proposal=value.get('proposal')
    if not isinstance(proposal,str) or not proposal.strip() or len(proposal)>4000:
        raise DeliberationContractError('Invalid shared proposal')
    return {'proposal':proposal, 'proposal_id':hashlib.sha256(proposal.encode()).hexdigest()[:16]}

def vote_response(text, proposal_id):
    value=object_response(text)
    if value.get('proposal_id')!=proposal_id or type(value.get('accept_shared_proposal')) is not bool:
        raise DeliberationContractError('Reviewer did not vote on the exact shared proposal')
    objections=value.get('blocking_objections')
    if not isinstance(objections,list) or len(objections)>10 or any(not isinstance(x,str) or not x.strip() or len(x)>1500 for x in objections):
        raise DeliberationContractError('Invalid blocking objections')
    revision=value.get('revision','')
    if not isinstance(revision,str) or len(revision)>4000:
        raise DeliberationContractError('Invalid reviewer revision')
    return {'proposal_id':proposal_id,'accept_shared_proposal':value['accept_shared_proposal'],
            'blocking_objections':objections,'revision':revision}

def unanimous(votes):
    return len(votes)==3 and all(v['accept_shared_proposal'] is True and not v['blocking_objections'] for v in votes)

def deliberate(task,context,sources,call,system,roles,progress=None,max_rounds=MAX_ROUNDS):
    if type(max_rounds) is not int or not 1<=max_rounds<=MAX_ROUNDS or len(roles)!=3:
        raise ValueError('Deliberation requires three reviewers and one to three rounds')
    progress=progress or (lambda stage,count:None)
    completed=0
    material={'task_paper':task,'lead_context':context,'sources':sources}
    def parallel(prompts,stage,validator=None):
        nonlocal completed
        progress(stage,completed)
        results=[None]*3
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures={pool.submit(call,system+'\nYour role: '+roles[i]+'\n'+instruction,
                                 json.dumps(payload,ensure_ascii=False),i):i
                     for i,(instruction,payload) in enumerate(prompts)}
            for future in as_completed(futures):
                text=future.result()
                results[futures[future]]=validator(text) if validator else text
                completed+=1; progress(stage,completed)
        return results
    findings=parallel([('Analyze independently within the supplied task scope. Return a concise findings report under 2400 characters: decision-relevant findings, precise source citations, unresolved uncertainties and one best proposed next step. Do not summarize the whole constitution or repeat the sources.',material)]*3,'independent_review')
    votes=[]; rounds=[]; consensus=False; proposal=None
    for round_number in range(1,max_rounds+1):
        progress('proposal_round_'+str(round_number),completed)
        proposal=proposal_response(call(system+'\nModerate the shared decision. Review all independent findings and previous blocking objections. Revise the proposal using evidence, not pressure for agreement. Return JSON ONLY: {"proposal":"one concrete scoped decision under 1200 characters"}. Do not declare consensus.',
                                       json.dumps({'material':material,'reviewer_findings':findings,'previous_proposal':proposal,'previous_votes':votes},ensure_ascii=False),3))
        completed+=1
        instruction='Read the exact shared proposal and all other reviewers\' reports/votes. Respond to their objections using source evidence. You may keep a dissent: do not agree to please the group. Return JSON ONLY: {"proposal_id":"the supplied id","accept_shared_proposal":true or false,"blocking_objections":["unresolved critical objection"],"revision":"your suggested revision or empty"}. Keep each objection under 500 characters and the suggested revision under 1200 characters. Approval with blocking objections is NOT agreement.'
        payload={'material':material,'reviewer_findings':findings,'shared_proposal':proposal,'previous_votes':votes,'round':round_number}
        votes=parallel([(instruction,payload)]*3,'discussion_round_'+str(round_number),lambda text:vote_response(text,proposal['proposal_id']))
        consensus=unanimous(votes)
        rounds.append({'round':round_number,'proposal':proposal,'votes':votes,'unanimous':consensus})
        if consensus:
            break
    progress('synthesis',completed)
    outcome={'consensus':consensus,'discussion_rounds':len(rounds),'proposal':proposal,'rounds':rounds}
    summary=call(system+'\nWrite one concise Arabic answer under 2500 characters. Explain the proposal, source evidence, unresolved uncertainty and exactly one next step. If consensus=false explicitly state that full agreement was NOT reached and present remaining objections; do not invent a final agreed decision. If consensus=true explain unanimity is not empirical proof. Never expose private deliberation or all transcripts.',
                 json.dumps({'material':material,'reviewer_findings':findings,'outcome':outcome},ensure_ascii=False),4)
    completed+=1
    # The application, not the synthesizer, supplies the definitive agreement label.
    label='اتفق المراجعون الثلاثة على الاقتراح؛ الاتفاق لا يثبت صحته تجريبيًا.' if consensus else 'لم يصل المراجعون الثلاثة إلى اتفاق كامل ضمن حد الجولات؛ الخلاف قائم ولا يوجد قرار جماعي نهائي.'
    progress('completed',completed)
    return label+'\n\n'+summary, {'reviewers':3,'discussion_rounds':len(rounds),'consensus':consensus,
                                 'syntheses':1,'model_requests':completed,'max_model_requests':MAX_REQUESTS}
