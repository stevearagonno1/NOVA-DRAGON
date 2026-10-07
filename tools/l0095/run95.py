"""Fixed four-case SOL CCI/Stochastic pulse vs state experiment."""
from pathlib import Path
import gzip,hashlib,json,math,time,statistics
import numpy as np
import research85 as H,signals85 as S,indicators84 as I
ROOT=Path(__file__).resolve().parent;H.ASSETS=['SOLUSDT']
BRANCH='agent/l0095-sol-momentum-state-2026-10-07'
DEST='history/research/hyp_lab_out/L0095-sol-momentum-state'
write=H.write_json
RULES=[{'id':'CCI_ONLY','meaning':'CCI7 crosses upward -100'},
       {'id':'CCI_AND_STOCH_PULSE','meaning':'CCI pulse AND Stoch21/5 upward cross, K<30,D<30'},
       {'id':'CCI_AND_STOCH_STATE_30','meaning':'CCI pulse AND K>D,K<30,D<30'},
       {'id':'CCI_AND_STOCH_STATE_ANY','meaning':'CCI pulse AND K>D without oversold cutoff'}]
def masks(d,reference=False):
    g=[{'family':'CCI','id':'CCI_7_-100','n':7,'t':-100},{'family':'STOCH','id':'STOCH_21_5_30','n':21,'d':5,'t':30}]
    built=S.build(d,g);cci=S.pulse(built['CCI_7_-100']);cross=S.pulse(built['STOCH_21_5_30']);k,v=I.stochastic(d['h'],d['l'],d['c'],21,5)
    if reference:
        kk=np.full(len(k),np.nan);vv=np.full(len(k),np.nan)
        for t in range(20,len(k)):
            low=min(float(x) for x in d['l'][t-20:t+1]);high=max(float(x) for x in d['h'][t-20:t+1]);kk[t]=100*(float(d['c'][t])-low)/(high-low) if high!=low else np.nan
        for t in range(24,len(k)):vv[t]=sum(float(x) for x in kk[t-4:t+1])/5
        assert np.allclose(k,kk,equal_nan=True) and np.allclose(v,vv,equal_nan=True)
        k,v=kk,vv
    truths=[cci,cci&cross,cci&(k>v)&(k<30)&(v<30),cci&(k>v)]
    return {q['id']:H.pack(S.pulse(x)) for q,x in zip(RULES,truths)}
def raw_input(synthetic):
    d=H.fixture()['SOLUSDT'] if synthetic else H.load_market()['SOLUSDT'];mm=masks(d)
    assert mm==masks(d,True),'Stochastic scalar reference masks differ'
    for cut in ([100,200,300] if synthetic else [1200,1800,2400]):
        pre=masks({k:v[:cut] for k,v in d.items()})
        assert all(pre[k]==(v&((1<<cut)-1)) for k,v in mm.items()),('prefix',cut)
    if synthetic:
        periods=[{'start':a,'end':b,'valid':list(range(a+5,b-24)),'events':H.labels(d,a,b)} for a,b in [(80,190),(195,305),(310,420)]]
    else:
        parent=json.loads(gzip.decompress((ROOT/'parent93.json.gz').read_bytes()))['assets']['SOLUSDT'];periods=parent['periods']
        assert mm['CCI_ONLY']==int(parent['masks']['CCI_7_-100'],16)
        # Pulse control must reproduce the original L0094 AND0 case exactly.
        a=int(parent['masks']['CCI_7_-100'],16);b=int(parent['masks']['STOCH_21_5_30'],16);assert mm['CCI_AND_STOCH_PULSE']==(a&b)&~((a&b)<<1)
    for p in periods:assert [(e['onset'],e['hit']) for e in p['events']]==H.labels_reference(d,p['start'],p['end'])
    return {'synthetic':synthetic,'rules':RULES,'masks':{k:hex(v) for k,v in mm.items()},'periods':periods,'times':d['dt']}
def evaluate(raw,reference=False):
    result=[];alerts=[]
    for q in RULES:
        mask=int(raw['masks'][q['id']],16);per=[];lags=[];captures=[]
        for pi,p in enumerate(raw['periods']):
            bars=[t for t in p['valid'] if mask>>t&1];claimed=set();hh=[];ll=[]
            for t in bars:
                hit=next((j for j,e in enumerate(p['events']) if j not in claimed and abs(t-e['onset'])<=2),None)
                if hit is not None:claimed.add(hit);hh.append(p['events'][hit]['onset']);ll.append(t-p['events'][hit]['onset'])
                alerts.append({'case':q['id'],'period':pi,'bar':t,'time':raw['times'][t],'onset':p['events'][hit]['onset'] if hit is not None else None})
            if reference:
                events=[{**e,'mask':sum(1<<t for t in e['window'])} for e in p['events']];x=sum(1<<t for t in bars);assert H.score(x,events)==(len(bars),len(claimed),sum(ll))
            per.append(H.metric(len(bars),len(claimed),len(p['events'])));captures.append(hh);lags+=ll
        ns=sum(v['signals'] for v in per);tp=sum(v['matched_events'] for v in per);ne=sum(v['events'] for v in per);z=1.959963984540054
        if ns:
            ph=tp/ns;den=1+z*z/ns;mid=(ph+z*z/(2*ns))/den;half=z*math.sqrt(ph*(1-ph)/ns+z*z/(4*ns*ns))/den;interval=[mid-half,mid+half]
        else:interval=None
        eligible=ns>=20 and tp/ne>=.3 and all(v['signals']>=3 and v['recall']>=.15 for v in per)
        result.append(dict(id=q['id'],**H.metric(ns,tp,ne),periods=per,captured_onsets=captures,median_lag=statistics.median(lags) if lags else None,wilson95=interval,eligible=eligible,
               quality_pass=eligible and tp/ns>=.7 and interval[0]>=.6 and statistics.median(lags)<=1))
    base=result[0]
    for r in result:
        r['added_vs_cci']=sum(len(set(a)-set(b)) for a,b in zip(r['captured_onsets'],base['captured_onsets']));r['lost_vs_cci']=sum(len(set(b)-set(a)) for a,b in zip(r['captured_onsets'],base['captured_onsets']))
        r['marginal_gain']=r['id']!='CCI_ONLY' and r['precision']>=base['precision']+.05 and r['recall']>=.8*base['recall']
    return result,alerts
def report(out,rows,synthetic):
    lines=['# L0095 — تأكيد زخم مستمر على SOL','', '1.أربعحالات CCI7/Stoch21/5،4h،ثلاثفترات2025.' if not synthetic else '1.فحص اصطناعي فقط؛لا سوق.',
           '2.المال:not measured.','3.4صفوف و12تقييممقطع؛العينةتنبيهاتوأحداث.','4.الربحيةوالتكاليف:not measured.','5.فترةعمياء:not measured.','6.الاحتفاظ:not measured.','7.Defer adoption؛مقارنةتطويرفقط.','8.التالي:مراجعةالقائد،لاتوسعةتلقائية.']
    def table(title,heads,data):
        lines.extend(['','## '+title,'|'+'|'.join(heads)+'|','|'+'|'.join(['---']*len(heads))+'|']);lines.extend('|'+'|'.join(map(str,v))+'|' for v in data)
    table('1.الهوية',['البند','القيمة'],[['العملة','SOLUSDT'],['الإطار','4hUTC'],['الفترات','يناير–مارس؛5أبريل–30يونيو؛5يوليو–30سبتمبر2025'],['المصدر','source.json,parent93.json.gz,SOLUSDT.csv'],['الفرق','حالةK>Dبدلالتقاطع؛الحالتانمعحد30وبدونه']])
    table('2.المال',['المقياس','الحالة'],[['الأرباح/التكاليف/الصفقات/الخروج','not measured — outside this phase']])
    table('3.الإشارات',['الحالة','تنبيهات','ملتقط/أحداث','الدقة','الاسترجاع','الأهلية'],[[r['id'],r['signals'],str(r['matched_events'])+'/'+str(r['events']),f"{r['precision']:.2%}",f"{r['recall']:.2%}",r['eligible']] for r in rows])
    table('4.العينةوالتوقيت',['الحالة','Wilson95وصفي','وسيطالتأخير'],[[r['id'],r['wilson95'],r['median_lag']] for r in rows])
    table('5.الثبات',['الحالة','المقطع','NS','P','R'],[[r['id'],i+1,v['signals'],f"{v['precision']:.2%}",f"{v['recall']:.2%}"] for r in rows for i,v in enumerate(r['periods'])])
    table('6.القيمةفوقCCI',['الحالة','أحداثمضافة','أحداثمفقودة','اجتياز+5نقاط/احتفاظ80%R'],[[r['id'],r['added_vs_cci'],r['lost_vs_cci'],r['marginal_gain']] for r in rows])
    table('7.الجودة',['الحالة','P70/R30/NS20/Wilsonlow60/lag≤1/ثبات','اجتيازالجودةوالإضافة'],[[r['id'],r['quality_pass'],r['quality_pass'] and r['marginal_gain']] for r in rows])
    lines+=['','البياناتتطويرتاريخيمكشوف؛لا تحققأعمىأودلالةمصححة. Wilsonوصفيباستقلالالتنبيهات. لااختياربعديفترةأوعتبةأفضلأواعتماد. raw.json.gzوأقنعةكلحالةوتسمياتالأحداثوالتوقيتتكفيلإعادةالحساب؛alerts.jsonيسجلجميعالتنبيهاتبمافيهاالكاذبة. لااختبارحالةزخمأخرىخارجالتعريفين.','إعادةالتشغيل:python launch95.py --fixture-onlyللاصطناعيأوpython launch95.py --out runللمهمةالمسجلة؛المصدرثابت.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
def execute(out,synthetic=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);begin=time.monotonic();source=json.loads((ROOT/'source.json').read_text())
    for name,digest in source['sha256'].items():assert H.sha(ROOT/name)==digest,name
    path=out/'raw.json.gz'
    if path.exists():
        checkpoint=json.loads((out/'checkpoint.json').read_text());assert checkpoint['source']==source and checkpoint['synthetic']==synthetic and checkpoint['raw_sha256']==H.sha(path);raw=json.loads(gzip.decompress(path.read_bytes()))
    else:
        raw=raw_input(synthetic);H.atomic(path,gzip.compress(json.dumps(raw,sort_keys=True).encode(),mtime=0));write(out/'checkpoint.json',dict(source=source,synthetic=synthetic,raw_sha256=H.sha(path)))
    rows,alerts=evaluate(raw);assert (rows,alerts)==evaluate(raw,True)
    write(out/'results.json',rows);write(out/'alerts.json',alerts)
    write(out/'selection.json',dict(cases=[q['id'] for q in RULES],reselection=False,validation_read=False,adoption='NOT AUTHORISED'))
    write(out/'audit.json',dict(status='PASS',synthetic=synthetic,rows=4,period_evaluations=12,scalar_stochastic_and_prefix_checks=True,raw_matching_reference=True,raw_sha256=H.sha(path),compute_seconds=time.monotonic()-begin))
    write(out/'analysis.json',dict(state='DEVELOPMENT_COMPARISON',quality_and_gain_passes=[r['id'] for r in rows if r['quality_pass'] and r['marginal_gain']],adoption='NOT AUTHORISED',next='Lead review only'))
    report(out,rows,synthetic)
