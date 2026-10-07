"""L0093: registered singleton discovery. Synthetic tests only on Lead side."""
from pathlib import Path
import argparse,base64,collections,gzip,hashlib,json,math,os,time,zipfile
import numpy as np
import research85 as R, signals85 as S
from candles92 import definitions,pattern

ROOT=Path(__file__).resolve().parent
BRANCH='agent/l0093-singleton-survey-2026-10-07'
DEST='history/research/hyp_lab_out/L0093-singleton-survey'
PERIODS=[('2025-01-01T00:00:00Z','2025-04-01T00:00:00Z'),('2025-04-05T00:00:00Z','2025-07-01T00:00:00Z'),('2025-07-05T00:00:00Z','2025-10-01T00:00:00Z')]
def write(p,x): R.write_json(p,x)
def grid():
    g=S.catalogue()+[dict(id='C92_'+str(i),family='C92_'+q['kind'],**q) for i,q in enumerate(definitions())]
    assert len(g)==482 and len({q['id'] for q in g})==482
    return g
def masks(d):
    result=S.build(d)
    result={k:R.pack(S.pulse(v)) for k,v in result.items()}
    result.update({'C92_'+str(i):R.pack(pattern(d,q)) for i,q in enumerate(definitions())})
    return result
def raw_fixture():
    raw={'synthetic':True,'grid':grid(),'assets':{}}
    for asset,d in R.fixture().items():
        periods=[]
        for start,end in [(80,190),(195,305),(310,420)]:
            ev=R.labels(d,start,end);assert [(e['onset'],e['hit']) for e in ev]==R.labels_reference(d,start,end)
            periods.append({'start':start,'end':end,'valid':list(range(start+5,end-24)),'events':ev})
        raw['assets'][asset]={'masks':{k:hex(v) for k,v in masks(d).items()},'periods':periods}
        # Full-grid causal prefix check, plus all six candle scalar definitions.
        short={k:v[:300] for k,v in d.items()};shortm=masks(short)
        for k,v in masks(d).items():assert shortm[k]==(v&((1<<300)-1)),k
        for q in definitions():assert np.array_equal(pattern(d,q),pattern(d,q,True))
    return raw
def raw_market():
    original=json.loads(gzip.decompress((ROOT/'parent_raw.json.gz').read_bytes()))
    out={'synthetic':False,'grid':grid(),'assets':{}}
    for asset,d in R.load_market().items():
        periods=original['assets'][asset]['periods']
        for p,(lo,hi) in zip(periods,PERIODS):
            assert d['dt'][p['start']]==lo
            assert d['dt'][p['end']]==hi if p['end']<len(d['dt']) else hi=='2025-10-01T00:00:00Z'
            assert [(e['onset'],e['hit']) for e in p['events']]==R.labels_reference(d,p['start'],p['end'])
        mm=masks(d)
        for cut in [1200,1800,2400]:
            part=masks({k:v[:cut] for k,v in d.items()})
            for k,v in mm.items():assert part[k]==(v&((1<<cut)-1)),('causality',asset,k,cut)
        out['assets'][asset]={'masks':{k:hex(v) for k,v in mm.items()},'periods':periods}
    return out
def wilson(ns,tp):
    if not ns:return None
    z=1.959963984540054;p=tp/ns;den=1+z*z/ns
    mid=(p+z*z/(2*ns))/den;half=z*math.sqrt(p*(1-p)/ns+z*z/(4*ns*ns))/den
    return [mid-half,mid+half]
def evaluate(raw,reference=False):
    rows=[]
    for asset,a in raw['assets'].items():
        for q in raw['grid']:
            pulse=int(a['masks'][q['id']],16);per=[];lags=[];hits=[]
            for pi,p in enumerate(a['periods']):
                x=pulse&sum(1<<b for b in p['valid'])
                events=[{**e,'mask':sum(1<<b for b in e['window'])} for e in p['events']]
                ns,tp,lag=(R.score_reference if reference else R.score)(x,events)
                hh=[];ll=[]
                for e in events:
                    common=x&e['mask']
                    if common:
                        hh.append(e['onset']);ll.append((common&-common).bit_length()-1-e['onset'])
                assert len(hh)==tp and sum(ll)==lag
                per.append(R.metric(ns,tp,len(events)));hits.append(hh);lags+=ll
            ns=sum(p['signals'] for p in per);tp=sum(p['matched_events'] for p in per);ne=sum(p['events'] for p in per)
            rows.append(dict(asset=asset,id=q['id'],family=q['family'],**R.metric(ns,tp,ne),periods=per,
                             captured_onsets=hits,median_lag=float(np.median(lags)) if lags else None,wilson95=wilson(ns,tp),
                             eligible=ns>=20 and tp/ne>=.3 and all(p['signals']>=3 and p['recall']>=.15 for p in per),
                             minimum_period_precision=min(p['precision'] for p in per)))
    assert len(rows)==1446
    return rows
def select(rows):
    result={}
    for asset in R.ASSETS:
        eligible=sorted([r for r in rows if r['asset']==asset and r['eligible']],key=lambda r:(-r['minimum_period_precision'],-r['wilson95'][0],-r['recall'],-r['signals'],r['id']))
        # One representative per family per asset; do not silently discard all other raw settings.
        picked={}
        for r in eligible:picked.setdefault(r['family'],r['id'])
        result[asset]=picked
    return {'per_asset_family_representatives':result,'validation_read':False,'adoption':'NOT AUTHORISED'}
def report(out,rows,synthetic):
    lines=['# L0093 — المسح المنفرد','',
           '1. 482 إعدادًا منفردًا؛ BTC/ETH/SOL،4h،ثلاث فترات2025 مسجلة.' if not synthetic else '1. فحص اصطناعي فقط؛لا نتائج سوق.',
           '2. المال: not measured — outside this phase.','3. الصفقات: not measured؛1446 صف عملة/إعداد،4338 تقييم مقطع.',
           '4. معامل الربح والتكاليف: not measured.','5. تحقق أعمى: not measured؛تطوير تاريخي مكشوف.',
           '6. الاحتفاظ: not measured.','7. Defer adoption؛الترتيب اكتشافي فقط.','8. التالي: مراجعة القائد،لا مزج تلقائي.']
    def tab(title,heads,data):
        lines.extend(['','## '+title,'|'+'|'.join(heads)+'|','|'+'|'.join(['---']*len(heads))+'|'])
        lines.extend('|'+'|'.join(map(str,r))+'|' for r in data)
    tab('1. الهوية',['البند','القيمة'],[['النطاق','476 من L0085 +6 تعريفات L0092؛لا دمج'],['الفترات','يناير–مارس؛5أبريل–30يونيو؛5يوليو–30سبتمبر2025'],['المصدر','scope.json/source.json؛الخام المحفوظ']])
    tab('2. المال',['المقياس','الحالة'],[['الأرباح/الصفقات/التكاليف/الخروج','not measured — outside this phase']])
    tab('3. جميع الإعدادات',['العملة','الإعداد','تنبيهات','ملتقط/أحداث','الدقة','الاسترجاع','الأهلية'],[[r['asset'],r['id'],r['signals'],str(r['matched_events'])+'/'+str(r['events']),f"{r['precision']:.2%}",f"{r['recall']:.2%}",r['eligible']] for r in rows])
    picked=select(rows)['per_asset_family_representatives']; chosen=[r for r in rows if picked[r['asset']].get(r['family'])==r['id']]
    tab('4. العينة والتوقيت',['العملة','الإعداد','Wilson95 وصفي','وسيط التأخير شمعة'],[[r['asset'],r['id'],r['wilson95'],r['median_lag']] for r in chosen])
    tab('5. الثبات',['العملة','الإعداد','المقطع','تنبيهات','الدقة','الاسترجاع'],[[r['asset'],r['id'],i+1,z['signals'],f"{z['precision']:.2%}",f"{z['recall']:.2%}"] for r in chosen for i,z in enumerate(r['periods'])])
    baselines=[]
    raw=json.loads(gzip.decompress((out/'raw.json.gz').read_bytes()))
    for asset,a in raw['assets'].items():
        for name in ['NONE','EVERY_BAR','EVERY_5_BARS']:
            ns=tp=ne=0
            for p in a['periods']:
                valid=p['valid'];x=0 if name=='NONE' else sum(1<<i for i in valid if name=='EVERY_BAR' or (i-valid[0])%5==0)
                events=[{**e,'mask':sum(1<<b for b in e['window'])} for e in p['events']]
                n,t,_=R.score_reference(x,events);ns+=n;tp+=t;ne+=len(events)
            baselines.append(dict(asset=asset,name=name,**R.metric(ns,tp,ne)))
    write(out/'baselines.json',baselines)
    tab('6. الضوابط',['العملة','الضابط','تنبيهات','الدقة','الاسترجاع'],[[r['asset'],r['name'],r['signals'],f"{r['precision']:.2%}",f"{r['recall']:.2%}"] for r in baselines])
    tab('7. الحكم',['المعيار','المطلوب','الحالة'],[['أهلية كل عملة','NS20/R30%؛كل مقطعNS3/R15%','مطبقة قبل ترتيب الاختيار'],['هدف الدقة','70% معR30% وNS20 وWilson lower60%','انظر quality.json؛وصفي فقط'],['اعتماد','تحقق منفصل','not measured؛NOT AUTHORISED']])
    quality=[dict(asset=r['asset'],id=r['id'],target_pass=r['precision']>=.7 and r['recall']>=.3 and r['signals']>=20 and r['eligible'] and r['wilson95'][0]>=.6 and r['median_lag']<=1) for r in rows]
    write(out/'quality.json',quality)
    lines+=['','الحكم Defer؛لا ادعاء أن أعلى دقة هي الأقوى عالميًا. Wilson وصفي بلا تصحيح اعتماد زمني أو البحث،والدلالة المصححة not measured. لا استبدال تحقق بمزيد من البحث على التاريخ نفسه.',
            'إعادة الحساب: `python run93.py --mode fixture --out fixture` أو `python run93.py --mode measure --out market`،مع ملف source.json ونفس الحزمة المثبتة.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
def execute(out,synthetic=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    source=json.loads((ROOT/'source.json').read_text())
    for name,h in source['sha256'].items():assert R.sha(ROOT/name)==h,('source changed',name)
    rawpath=out/'raw.json.gz';begin=time.monotonic()
    if rawpath.exists():
        checkpoint=json.loads((out/'checkpoint.json').read_text());assert checkpoint['source']==source and checkpoint['synthetic']==synthetic
        assert R.sha(rawpath)==checkpoint['raw_sha256'];raw=json.loads(gzip.decompress(rawpath.read_bytes()))
    else:
        raw=raw_fixture() if synthetic else raw_market();R.atomic(rawpath,gzip.compress(json.dumps(raw,sort_keys=True).encode(),mtime=0))
        write(out/'checkpoint.json',dict(source=source,synthetic=synthetic,raw_sha256=R.sha(rawpath)))
    rows=evaluate(raw);assert rows==evaluate(raw,True),'independent scalar matching mismatch'
    write(out/'results.json',rows);write(out/'selection.json',select(rows))
    write(out/'audit.json',dict(status='PASS',synthetic=synthetic,settings=482,rows=1446,period_evaluations=4338,independent_scalar_matching=True,raw_sha256=R.sha(rawpath),indicator_reference_limit='Inherited EMA/RSI/BB tests;not every indicator independently reimplemented',compute_seconds=time.monotonic()-begin))
    report(out,rows,synthetic)
    write(out/'analysis.json',dict(state='DISCOVERY_ONLY',adoption='NOT AUTHORISED',quality_passes=[q for q in json.loads((out/'quality.json').read_text()) if q['target_pass']],next='Lead review;no automatic pairs or validation'))
    return rows
def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['fixture','measure'],required=True);p.add_argument('--out',required=True);a=p.parse_args()
    execute(a.out,a.mode=='fixture');print('PASS '+a.mode,flush=True)
if __name__=='__main__':main()
