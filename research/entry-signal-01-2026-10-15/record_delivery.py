"""Append the prepared research record after verified delivery; never change results."""
import argparse,base64,json,os,time
from pathlib import Path
from delivery import API,publish,REPO
P=Path(__file__).resolve().parent
def main(rehearsal):
    mode='rehearsal' if rehearsal else 'execution';out=P/mode
    receipt=json.loads((out/'LOCAL-RECEIPT.json').read_text());spec=json.loads((P/'protocol.json').read_text())
    branch=spec['readiness_branch'] if rehearsal else spec['execution_branch']
    assert receipt['receipt_delivery']['branch']==branch
    api=API(os.environ.get('GH_TOKEN',''));prefix='/repos/'+REPO
    head=api.call('GET',prefix+'/git/ref/heads/'+branch)['object']['sha']
    assert head==receipt['receipt_delivery']['commit'],'Branch moved; inspect before recording'
    commit=api.call('GET',prefix+'/git/commits/'+head)
    root=api.call('GET',prefix+'/git/trees/'+commit['tree']['sha'])
    log=next(x for x in root['tree'] if x['path']=='LOG.md')
    old=base64.b64decode(api.call('GET',prefix+'/git/blobs/'+log['sha'])['content'])
    text='\n\n## Entry single-signal '+mode+' — 2026-10-15\nFixed independent alert conditions calculated and integrity checked; verified data at '+receipt['data_delivery']['commit']+'. No combination, financial result, selection or validation. Full evidence: '+spec['repository_path']+mode+'/ .\n'
    (out/'LOG-APPEND.md').write_bytes(old+text.encode())
    tick='القرار: '+('فحص مسار المهمة على بيانات مصطنعة فقط.' if rehearsal else 'اكتشاف وصفي لإشارات الدخول المستقلة فقط.')+'\nالتنفيذ: حساب الشروط المقفلة والتحقق من الصعود بعد الإشارة والتوقيت والتعداد ثم رفع الأدلة والتحقق منها.\nالناتج: نتائج وصفية وسجل كامل؛ لا مخارج أو ربح أو دمج أو اعتماد إشارة.\nالتالي: مراجعة القائد للأدلة قبل أي جولة أخرى.\n'
    (out/'TICK.md').write_text(tick)
    files={'LOG.md':out/'LOG-APPEND.md','docs/journal/2026-10-15-entry-signal/'+('001-readiness.md' if rehearsal else '001-single-discovery.md'):out/'TICK.md'}
    final=publish(api,branch,head,files)
    result={'status':'PASS_REHEARSAL_ONLY' if rehearsal else 'ENTRY_DISCOVERY_DELIVERED_RECORDED_LEAD_REVIEW_PENDING','source_commit':receipt['source_commit'],'data_delivery':receipt['data_delivery'],'receipt_delivery':receipt['receipt_delivery'],'record_delivery':final,'scope':'entry alerts and subsequent price description only'}
    (out/'FINAL-RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n')
    print('تم')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--rehearsal',action='store_true');a=p.parse_args()
    try:main(a.rehearsal)
    except Exception as e:
        s=str(e);token=os.environ.get('GH_TOKEN','')
        if token:s=s.replace(token,'[REDACTED]')
        (P/'RECORD-ERROR.json').write_text(json.dumps({'cause':s},ensure_ascii=False)+'\n')
        print('فشل: '+(s.replace('\n',' ') or type(e).__name__)[:400]);raise SystemExit(1)
