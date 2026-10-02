#!/usr/bin/env python3
"""Bounded repeated deliberation: unanimity is validated, never inferred from prose."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import re

MAX_ROUNDS=3
MAX_REQUESTS=16
MAX_EVIDENCE_CHARS=16000

def numbered_sources(sources):
    return [dict(source,content='\n'.join('L'+str(i)+': '+line for i,line in
                                         enumerate(source['content'].splitlines(),1))) for source in sources]

def evidence_packet(sources,reports):
    """Copy cited lines from the pinned originals; never trust generated quotations."""
    text=json.dumps(reports,ensure_ascii=False)
    excerpts=[]; missing=[]; used=0
    for source in sources:
        path=source.get('path',''); lines=source['content'].splitlines()
        if not path: continue
        refs=set((int(a),int(b or a)) for a,b in re.findall(
            re.escape(path)+r':L(\d+)(?:-L?(\d+))?',text))
        for start,end in sorted(refs):
            ref=path+':L'+str(start)+'-L'+str(end)
            if not 1<=start<=end<=len(lines) or end-start>=80:
                missing.append(ref); continue
            # One context line on each side, still from the exact pinned source.
            lo=max(1,start-1); hi=min(len(lines),end+1)
            content='\n'.join('L'+str(i)+': '+lines[i-1] for i in range(lo,hi+1))
            if used+len(content)>MAX_EVIDENCE_CHARS:
                missing.append(ref); continue
            excerpts.append({key:source[key] for key in ('path','commit','blob_sha') if key in source} |
                            {'start_line':lo,'end_line':hi,'content':content})
            used+=len(content)
    return {'source_manifest':[{key:s[key] for key in ('path','commit','blob_sha') if key in s} for s in sources],
            'source_excerpts':excerpts,'unavailable_citations':missing,
            'evidence_complete':not sources or bool(excerpts) and not missing,
            'full_sources_omitted':bool(sources)}

class DeliberationContractError(ValueError):
    pass

def object_response(text):
    if not isinstance(text,str) or len(text)>30000:
        raise DeliberationContractError('Invalid structured deliberation response')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:
                raise DeliberationContractError('Duplicate structured response field')
            result[key]=value
        return result
    decoder=json.JSONDecoder(object_pairs_hook=pairs)
    try:
        value=decoder.decode(text.strip())
    except json.JSONDecodeError:
        # Allow a single complete JSON object surrounded by prose or a code fence.
        # Never repair values, truncated JSON, duplicates or conflicting objects.
        objects=[]; offset=0
        while offset<len(text):
            start=text.find('{',offset)
            if start<0: break
            try:
                value,end=decoder.raw_decode(text,start)
            except json.JSONDecodeError:
                raise DeliberationContractError('Incomplete or malformed structured response') from None
            objects.append(value); offset=end
        if len(objects)!=1:
            raise DeliberationContractError('Deliberation response must contain one complete JSON object') from None
        value=objects[0]
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
    material={'task_paper':task,'lead_context':context,'sources':numbered_sources(sources)}
    def compact(reports):
        return {'task_paper':task,'lead_context':context,**evidence_packet(sources,reports)}
    def parallel(prompts,stage,validator=None):
        nonlocal completed
        progress(stage,completed)
        results=[None]*3
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures={pool.submit(call,system+'\nYour role: '+roles[i]+'\n'+instruction,
                                 json.dumps(payload,ensure_ascii=False),i):i
                     for i,(instruction,payload) in enumerate(prompts)}
            for future in as_completed(futures):
                text=future.result()
                results[futures[future]]=validator(text) if validator else text
                completed+=1; progress(stage,completed)
        return results
    findings=parallel([('Analyze independently within the supplied task scope. Return a concise findings report under 2400 characters: decision-relevant findings, precise source citations, unresolved uncertainties and one best proposed next step. Cite each source claim using exactly path:Lstart-Lend (at most 80 lines per citation), with its commit. These references select the original evidence supplied to later rounds, so include the decisive constitution rules and task evidence. Do not summarize the whole constitution or repeat the sources.',material)]*3,'independent_review')
    votes=[]; rounds=[]; consensus=False; proposal=None
    for round_number in range(1,max_rounds+1):
        progress('proposal_round_'+str(round_number),completed)
        round_material=compact([findings,proposal,votes])
        proposal=proposal_response(call(system+'\nModerate the shared decision. Review all independent findings and previous blocking objections. Full files were read in the independent phase; now use only pinned source excerpts. Findings are claims, not verified evidence. Preserve path:Lstart-Lend citations in the proposal. Do not infer omitted source text or claim missing evidence was checked. Revise using evidence, not pressure for agreement. Return JSON ONLY: {"proposal":"one concrete scoped decision under 1200 characters"}. Do not declare consensus.',
                                       json.dumps({'material':round_material,'reviewer_findings':findings,'previous_proposal':proposal,'previous_votes':votes},ensure_ascii=False),3))
        completed+=1
        instruction='Read the exact shared proposal and all other reviewers\' reports/votes. Respond to their objections using source evidence. You may keep a dissent: do not agree to please the group. Return JSON ONLY: {"proposal_id":"the supplied id","accept_shared_proposal":true,"blocking_objections":["unresolved critical objection"],"revision":"your suggested revision or empty"}. Keep each objection under 500 characters and the suggested revision under 1200 characters. The displayed JSON is a schema example, not an approval instruction: use false when you disagree, and [] when no blocking objections remain. No prose or Markdown fences around JSON. Approval with blocking objections is NOT agreement.'
        round_material=compact([findings,proposal,votes])
        instruction+=' Full files are deliberately omitted after independent review. Verify source claims against the supplied pinned excerpts, not another reviewer\'s assertion. Missing context or unavailable citations are blocking uncertainties; do not approve unsupported source claims. Cite path:Lstart-Lend for evidence needed in a revision.'
        payload={'material':round_material,'reviewer_findings':findings,'shared_proposal':proposal,'previous_votes':votes,'round':round_number}
        votes=parallel([(instruction,payload)]*3,'discussion_round_'+str(round_number),lambda text:vote_response(text,proposal['proposal_id']))
        if not round_material['evidence_complete']:
            for vote in votes:
                vote['accept_shared_proposal']=False
                vote['blocking_objections'].append('Pinned source citations are missing, invalid or exceed the evidence budget; source-backed agreement cannot be validated.')
        consensus=unanimous(votes)
        rounds.append({'round':round_number,'proposal':proposal,'votes':votes,'unanimous':consensus})
        if consensus:
            break
    progress('synthesis',completed)
    outcome={'consensus':consensus,'discussion_rounds':len(rounds),'proposal':proposal,'rounds':rounds}
    summary=call(system+'\nWrite one concise Arabic answer under 2500 characters. Explain the proposal, source evidence, unresolved uncertainty and exactly one next step. If consensus=false explicitly state that full agreement was NOT reached and present remaining objections; do not invent a final agreed decision. If consensus=true explain unanimity is not empirical proof. Never expose private deliberation or all transcripts.',
                 json.dumps({'material':compact([findings,outcome]),'reviewer_findings':findings,'outcome':outcome},ensure_ascii=False),4)
    completed+=1
    # The application, not the synthesizer, supplies the definitive agreement label.
    label='اتفق المراجعون الثلاثة على الاقتراح؛ الاتفاق لا يثبت صحته تجريبيًا.' if consensus else 'لم يصل المراجعون الثلاثة إلى اتفاق كامل ضمن حد الجولات؛ الخلاف قائم ولا يوجد قرار جماعي نهائي.'
    progress('completed',completed)
    return label+'\n\n'+summary, {'reviewers':3,'discussion_rounds':len(rounds),'consensus':consensus,
                                 'syntheses':1,'model_requests':completed,'max_model_requests':MAX_REQUESTS}
