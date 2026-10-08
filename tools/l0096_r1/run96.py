"""Fixed twelve-case SOL CCI prior depth and closed-candle recovery experiment."""
from pathlib import Path
import gzip,hashlib,json,math,time,statistics
import numpy as np
import research85 as H,signals85 as S,indicators84 as I
ROOT=Path(__file__).resolve().parent;H.ASSETS=['SOLUSDT']
BRANCH='agent/l0096-sol-depth-recovery-r1-2026-10-08'
DEST='history/research/hyp_lab_out/L0096-sol-depth-recovery-r1'
write=H.write_json
RULES=[{'id':'CCI_ONLY','depth':None,'recovery':None}]
for depth in [2,3,4]:RULES.append({'id':f'CCI_DEPTH_{depth}','depth':depth,'recovery':None})
for recovery in [0,.25]:RULES.append({'id':f'CCI_RECOVERY_{recovery}','depth':None,'recovery':recovery})
for depth in [2,3,4]:
    for recovery in [0,.25]:RULES.append({'id':f'CCI_DEPTH_{depth}_RECOVERY_{recovery}','depth':depth,'recovery':recovery})
def masks(d,reference=False):
    g=[{'family':'CCI','id':'CCI_7_-100','n':7,'t':-100}];cci=S.pulse(S.build(d,g)['CCI_7_-100'])
    c=d['c'];a=I.wilder_atr(d['h'],d['l'],c,14)
    depth=np.full(len(c),np.nan);recovery=np.full(len(c),np.nan)
    for t in range(1,len(c)):
        if not np.isfinite(a[t-1]) or a[t-1]<=0:continue
        recovery[t]=(c[t]-c[t-1])/a[t-1]
        if t>=18:depth[t]=(max(d['h'][t-18:t])-c[t-1])/a[t-1]
    if reference:
        out={}
        for q in RULES:
            truth=[]
            for t in range(len(c)):
                ok=bool(cci[t])
                if q['depth'] is not None:
                    ok=ok and t>=18 and np.isfinite(a[t-1]) and a[t-1]>0 and (max(float(d['h'][j]) for j in range(t-18,t))-float(c[t-1]))>=q['depth']*float(a[t-1])
                if q['recovery'] is not None:
                    ok=ok and t>0 and np.isfinite(a[t-1]) and a[t-1]>0 and float(c[t])>float(d['o'][t]) and float(c[t])-float(c[t-1])>=q['recovery']*float(a[t-1])
                truth.append(bool(ok))
            out[q['id']]=sum(1<<t for t,v in enumerate(truth) if v and (t==0 or not truth[t-1]))
        return out
    out={}
    for q in RULES:
        truth=cci.copy()
        if q['depth'] is not None:truth=truth&(depth>=q['depth'])
        if q['recovery'] is not None:truth=truth&(c>d['o'])&(recovery>=q['recovery'])
        out[q['id']]=H.pack(S.pulse(truth))
    return out
def raw_input(synthetic):
    d=H.fixture()['SOLUSDT'] if synthetic else H.load_market()['SOLUSDT'];mm=masks(d)
    assert mm==masks(d,True),'scalar depth/recovery masks differ'
    for cut in ([100,200,300] if synthetic else [1200,1800,2400]):
        pre=masks({k:v[:cut] for k,v in d.items()})
        assert all(pre[k]==(v&((1<<cut)-1)) for k,v in mm.items()),('prefix',cut)
    if synthetic:
        periods=[{'start':a,'end':b,'valid':list(range(a+5,b-24)),'events':H.labels(d,a,b)} for a,b in [(80,190),(195,305),(310,420)]]
    else:
        parent=json.loads(gzip.decompress((ROOT/'parent93.json.gz').read_bytes()))['assets']['SOLUSDT'];periods=parent['periods']
        assert mm['CCI_ONLY']==int(parent['masks']['CCI_7_-100'],16)
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
    lines=['# L0096 — عمق الهبوط واسترداد السعر على SOL','', '1.12حالة CCI7/عمقهبوط/استردادسعر،4h،ثلاثفترات2025.' if not synthetic else '1.فحص اصطناعي فقط؛لا سوق.',
           '2.المال:not measured.','3.12صفًا و36تقييممقطع؛العينةتنبيهاتوأحداث.','4.الربحيةوالتكاليف:not measured.','5.فترةعمياء:not measured.','6.الاحتفاظ:not measured.','7.Defer adoption؛مقارنةتطويرفقط.','8.التالي:مراجعةالقائد،لاتوسعةتلقائية.']
    def table(title,heads,data):
        lines.extend(['','## '+title,'|'+'|'.join(heads)+'|','|'+'|'.join(['---']*len(heads))+'|']);lines.extend('|'+'|'.join(map(str,v))+'|' for v in data)
    table('1.الهوية',['البند','القيمة'],[['العملة','SOLUSDT'],['الإطار','4hUTC'],['الفترات','يناير–مارس؛5أبريل–30يونيو؛5يوليو–30سبتمبر2025'],['المصدر','source.json,parent93.json.gz,SOLUSDT.csv'],['الفرق','عمقهبوط18شمعةسابقة≥2/3/4ATR،واسترداد0/0.25ATRمعشمعةصاعدة']])
    table('2.المال',['المقياس','الحالة'],[['الأرباح/التكاليف/الصفقات/الخروج','not measured — outside this phase']])
    table('3.الإشارات',['الحالة','تنبيهات','ملتقط/أحداث','الدقة','الاسترجاع','الأهلية'],[[r['id'],r['signals'],str(r['matched_events'])+'/'+str(r['events']),f"{r['precision']:.2%}",f"{r['recall']:.2%}",r['eligible']] for r in rows])
    table('4.العينةوالتوقيت',['الحالة','Wilson95وصفي','وسيطالتأخير'],[[r['id'],r['wilson95'],r['median_lag']] for r in rows])
    table('5.الثبات',['الحالة','المقطع','NS','P','R'],[[r['id'],i+1,v['signals'],f"{v['precision']:.2%}",f"{v['recall']:.2%}"] for r in rows for i,v in enumerate(r['periods'])])
    table('6.القيمةفوقCCI',['الحالة','أحداثمضافة','أحداثمفقودة','اجتياز+5نقاط/احتفاظ80%R'],[[r['id'],r['added_vs_cci'],r['lost_vs_cci'],r['marginal_gain']] for r in rows])
    table('7.الجودة',['الحالة','P70/R30/NS20/Wilsonlow60/lag≤1/ثبات','اجتيازالجودةوالإضافة'],[[r['id'],r['quality_pass'],r['quality_pass'] and r['marginal_gain']] for r in rows])
    lines+=['','البياناتتطويرتاريخيمكشوف؛لا تحققأعمىأودلالةمصححة. Wilsonوصفيباستقلالالتنبيهات. لااختياربعديفترةأوعتبةأفضلأواعتماد. raw.json.gzوأقنعةكلحالةوتسمياتالأحداثوالتوقيتتكفيلإعادةالحساب؛alerts.jsonيسجلجميعالتنبيهاتبمافيهاالكاذبة. لااختبارعتبةعمقأواستردادخارجالشبكة.','إعادةالتشغيل:python launch95.py --fixture-onlyللاصطناعيأوpython launch95.py --out runللمهمةالمسجلة؛المصدرثابت.']
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
    write(out/'audit.json',dict(status='PASS',synthetic=synthetic,rows=12,period_evaluations=36,scalar_depth_recovery_and_prefix_checks=True,raw_matching_reference=True,raw_sha256=H.sha(path),compute_seconds=time.monotonic()-begin))
    write(out/'analysis.json',dict(state='DEVELOPMENT_COMPARISON',quality_and_gain_passes=[r['id'] for r in rows if r['quality_pass'] and r['marginal_gain']],adoption='NOT AUTHORISED',next='Lead review only'))
    report(out,rows,synthetic)
