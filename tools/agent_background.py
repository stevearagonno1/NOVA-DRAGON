"""Two bounded read-only workers and one lead synthesis; no consensus loop."""
from concurrent.futures import ThreadPoolExecutor, wait
import json
import time
from agent_deliberation import numbered_sources, evidence_packet
from agent_council_transport import safe_reason

ROLES=('Analyze the scoped question and recommend one evidence-backed next step.',
       'Independently audit the question: check source alignment, risks and missing evidence. Do not assume the analyst is correct.')

def coordinate(task,context,sources,call,system,progress=None,worker_seconds=360,synthesis_seconds=240):
    progress=progress or (lambda phase,count:None)
    material={'task':task,'context':context,'sources':numbered_sources(sources)}
    worker_deadline=time.monotonic()+worker_seconds
    progress('subagents',0)
    pool=ThreadPoolExecutor(max_workers=2)
    futures={pool.submit(call,system+'\nYou are a delegated read-only worker. '+role+
                         '\nReturn a short Arabic findings report under 2000 characters. Cite decisive evidence as path:Lstart-Lend with commit. State uncertainty. No tools, execution, agreement votes or further delegation.',
                         json.dumps(material,ensure_ascii=False),i+1,worker_deadline):i
             for i,role in enumerate(ROLES)}
    done,pending=wait(futures,timeout=max(0,worker_deadline-time.monotonic()))
    reports=[]; failures=[]
    try:
        for future in sorted(done,key=lambda f:futures[f]):
            try:
                report=future.result()
                if not isinstance(report,str) or not report.strip():raise ValueError('Empty worker result')
                reports.append({'worker':futures[future]+1,'role':ROLES[futures[future]],'findings':report})
            except Exception as exc:
                failures.append({'worker':futures[future]+1,'reason_code':safe_reason(exc)['code']})
        for future in pending:
            future.cancel()
            failures.append({'worker':futures[future]+1,'reason_code':'worker_deadline'})
    finally:
        pool.shutdown(wait=False,cancel_futures=True)
    progress('subagents',len(reports))
    if not reports:raise TimeoutError('No worker result completed within its budget')
    progress('lead_synthesis',len(reports))
    evidence=evidence_packet(sources,reports)
    summary=call(system+'\nYou are the lead coordinator. Produce one short Arabic answer under 2200 characters: conclusion, source evidence, uncertainty and exactly one next step. Resolve differing findings with evidence; never invent consensus. If any worker failed, explicitly say which role was unavailable and do not claim a full audit. If evidence_complete=false, state that source verification is incomplete; do not certify source alignment. No private transcripts, tools or unperformed measurements.',
                 json.dumps({'task':task,'context':context,'workers':reports,'unavailable_workers':failures,
                             'evidence':evidence},ensure_ascii=False),0,time.monotonic()+synthesis_seconds)
    counts={'mode':'lead_and_subagents','subagents':2,'completed_subagents':len(reports),
            'unavailable_subagents':failures,'partial':bool(failures),
            'evidence_complete':evidence['evidence_complete'],'discussion_rounds':0,
            'model_requests':len(reports)+1,'max_model_requests':3}
    label='جمع العقل الرئيسي نتائج الفرعيين؛ لا توجد حلقة إجماع.'
    if failures:label+=' النتيجة جزئية: اكتمل '+str(len(reports))+' من فرعيين؛ المراجعة غير مكتملة.'
    if not evidence['evidence_complete']:label+=' التحقق من الأدلة المصدرية غير مكتمل.'
    progress('completed',counts['model_requests'])
    return label+'\n\n'+summary,counts
