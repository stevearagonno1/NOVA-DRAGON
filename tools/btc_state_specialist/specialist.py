"""BTC conditional-state discovery. No trades, full-stream precision or adoption."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse, csv, gzip, hashlib, io, json, math, os, time, fcntl
import numpy as np
import pandas as pd
import indicators84 as I
import signals85 as A
import signals88 as B
import candles92 as C

ROOT=Path(__file__).resolve().parent
MONTHS=['2021-12','2023-05','2023-12','2024-01','2025-05','2025-12','2026-03']
SEED=18102026
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def encode(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n').encode()
def workspace_bytes(p):return sum(x.stat().st_size for x in Path(p).rglob('*') if x.is_file() and not x.is_symlink())
def atomic(p,b):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    if workspace_bytes(os.environ.get('NOVA_WORKSPACE',ROOT.parent))+len(b)>125000000:raise RuntimeError('125 MB workspace limit')
    if p.exists():
        if p.read_bytes()!=b:raise RuntimeError('existing output differs: '+str(p))
        return
    tmp=p.with_suffix(p.suffix+'.pending')
    with tmp.open('wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
    os.replace(tmp,p)
def jsonout(p,x):atomic(p,encode(x))
def day(t):return (datetime.fromtimestamp(float(t),timezone.utc)+timedelta(hours=3)).strftime('%Y-%m-%d')
def month(t):return day(t)[:7]
def grid():return json.loads((ROOT/'grid.json').read_text())
def fingerprint(synthetic):
    code={p.name:sha(p) for p in ROOT.glob('*.py')}
    settings={'code':code,'grid':grid(),'inputs':json.loads((ROOT/'inputs.json').read_text()),'fixture':synthetic,'registration':json.loads((ROOT/'registration.json').read_text()),'definitions_sha256':sha(ROOT/'definitions.json'),'coverage_sha256':sha(ROOT/'coverage_scope.json'),'numpy':np.__version__,'pandas':pd.__version__}
    return hashlib.sha256(encode(settings)).hexdigest()
def runs(truth,days):
    out=[];start=None
    for i,v in enumerate(truth):
        if start is not None and (not v or days[i]!=days[i-1]):out.append((start,i-1));start=None
        if v and start is None:start=i
    if start is not None:out.append((start,len(truth)-1))
    return out
def state_mask(d,m):
    c,h=d['c'],d['h'];n=len(c);truth=np.zeros(n,bool)
    prevhigh=pd.Series(h).shift().rolling(12,min_periods=12).max().to_numpy()
    complete=pd.Series(d['minutes']==15).rolling(61,min_periods=61).sum().to_numpy()==61
    for i in range(260,n):
        truth[i]=complete[i] and month(d['dt'][i])==m and day(d['dt'][i])==day(d['dt'][i-4]) and c[i]/c[i-4]-1>=.005 and c[i]>prevhigh[i]
    return truth
def masks(d,g):
    out={};native=[{'id':q['id'],'family':q['family'],**q['settings']} for q in g if q['origin']=='registered_L0085_setting']
    for k,v in A.build(d,native).items():out[k]=A.pulse(v)
    later=[{'id':q['id'],'family':q['family'],**q['settings']} for q in g if q['origin']=='registered_L0088_setting']
    out.update(B.primitives(d,grid=later))
    obv=np.cumsum(np.r_[0,np.sign(np.diff(d['c']))]*d['v'])
    for q in g:
        ident=q['id'];cfg=q['settings'];origin=q['origin']
        if origin=='registered_older_52_grid':out[ident]=A.pulse(I.build_one(d,cfg['setting_name']))
        elif origin=='registered_L0090_volume_state':
            f,s=I.ema(obv,cfg['fast']),I.ema(obv,cfg['slow']);out[ident]=np.isfinite(f)&np.isfinite(s)&(np.round(f-s,10)>0)
        elif origin=='registered_L0091_setting':
            truth=np.zeros(len(obv),bool);n=cfg['n']
            for i in range(max(n,2),len(obv)):truth[i]=d['c'][i]>max(d['h'][i-n:i]) and (not cfg['no_lower_low'] or d['l'][i]>=min(d['l'][i-2:i]))
            out[ident]=A.pulse(truth)
        elif origin=='registered_L0092_setting':out[ident]=C.signals(d,{**cfg,'asset':'BTCUSDT'})
    assert set(out)=={q['id'] for q in g},'grid/implementation mismatch'
    return out
def fixture():
    n=420;x=np.arange(n);rng=np.random.default_rng(SEED)
    c=100+4*np.sin(x/11)+.2*np.sin(x/2)+rng.normal(0,.025,n);o=np.r_[c[0],c[:-1]]
    h=np.maximum(o,c)+.05;l=np.minimum(o,c)-.05;v=100+20*np.sin(x/3)+rng.uniform(0,20,n)
    start=datetime(2023,12,31,21,tzinfo=timezone.utc).timestamp()+899.999
    return {'o':o,'h':h,'l':l,'c':c,'v':v,'tbv':np.full(n,np.nan),'minutes':np.full(n,15),'dt':start+x*900}
def load_data(path):
    b=pd.read_csv(path);cols=[x for x in ['close_time_utc','time_utc'] if x in b]
    assert len(cols)==1,'expected exactly one verified candle close timestamp column'
    col=cols[0]
    dt=pd.to_datetime(b[col],utc=True).astype('int64').to_numpy()/1e9
    assert len(dt)>260 and np.allclose(np.diff(dt),900,atol=1e-6,rtol=0),'gap/order'
    d={k:b[name].to_numpy(float) for k,name in zip(['o','h','l','c','v'],['open','high','low','close','volume'])}
    assert all(np.isfinite(v).all() for v in d.values())
    assert ((d['l']<=np.minimum(d['o'],d['c']))&(d['h']>=np.maximum(d['o'],d['c']))&(d['l']>0)&(d['v']>=0)).all()
    d.update(dt=dt,minutes=b['minutes'].to_numpy(int),tbv=np.full(len(dt),np.nan));assert (d['minutes']==15).all()
    return d
def score(alerts,states):
    first=[];delays=[];counts=[]
    for start,end in states:
        hit=np.flatnonzero(alerts[start:end+1]);counts.append(len(hit))
        if len(hit):first.append(start+int(hit[0]));delays.append(int(hit[0]))
    return {'alerts':sum(counts),'caught':len(first),'missed':len(states)-len(first),'repeated':sum(max(0,n-1) for n in counts),'delays':delays,'first_indices':first}
def wilson(k,n):
    if not n:return [None,None]
    p=k/n;z=1.959963984540054;den=1+z*z/n;mid=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [mid-half,mid+half]
def pack(x):return hex(sum(1<<int(i) for i in np.flatnonzero(x)))
def unpack(x,n):
    a=int(x,16);return np.array([bool((a>>i)&1) for i in range(n)])
def summarize(ident,alerts,states,d,state,m):
    s=score(alerts,states);ne=len(states);s.update(candidate_id=ident,month=m,states=ne,state_bars=int(state.sum()),coverage=s['caught']/ne if ne else None,wilson95=wilson(s['caught'],ne),precision='not measured: conditional positive-only sample',median_delay_bars=float(np.median(s['delays'])) if s['delays'] else None)
    # Dependence-aware day resampling; empty sampled states => missing draw, not zero coverage.
    days=sorted(set(day(d['dt'][i]) for i,j in states));counts=[];hits=[]
    for date in days:
        sub=[(i,j) for i,j in states if day(d['dt'][i])==date];counts.append(len(sub));hits.append(score(alerts,sub)['caught'])
    if counts:
        rng=np.random.default_rng(SEED);ix=rng.integers(0,len(days),(1000,len(days)));den=np.array(counts)[ix].sum(1);num=np.array(hits)[ix].sum(1);s['day_bootstrap95']=list(map(float,np.quantile(num[den>0]/den[den>0],[.025,.975])))
    else:s['day_bootstrap95']=[None,None]
    s['median_remaining_close_gain_pct']=float(np.median([(max(d['c'][i:j+1])/d['c'][i]-1)*100 for i in s['first_indices'] for a,j in states if a<=i<=j])) if s['first_indices'] else None
    return s
def measure_one(d,m,g):
    state=state_mask(d,m);states=runs(state,[day(t) for t in d['dt']]);raw=masks(d,g)
    # Validate prefixes for every candidate before scoring; labels never enter masks().
    prefix=0
    for cut in sorted(set([max(260,len(d['c'])//2),len(d['c'])-20])):
        pre=masks({k:v[:cut] for k,v in d.items()},g)
        for ident in raw:assert np.array_equal(pre[ident],raw[ident][:cut]),('prefix',ident,cut);prefix+=1
    eligible=np.flatnonzero(state);entries=np.zeros(len(state),bool)
    for i,j in states:entries[i]=True
    raw.update(BASELINE_ALL_STATE_BARS=state,BASELINE_STATE_ENTRY=entries,BASELINE_NO_SIGNAL=np.zeros(len(state),bool))
    results=[];evidence={}
    for ident,mask in raw.items():
        selected=mask&state;s=summarize(ident,selected,states,d,state,m)
        rng=np.random.default_rng(SEED+int(hashlib.sha256(ident.encode()).hexdigest()[:8],16));control=np.zeros(len(state),bool)
        if selected.sum():control[rng.choice(eligible,int(selected.sum()),replace=False)]=True
        ctrl=score(control,states);s['matched_count_random_state_coverage']=ctrl['caught']/len(states) if states else None
        results.append(s);evidence[ident]=pack(selected)
    payload={'month':m,'timestamps':d['dt'].tolist(),'close':d['c'].tolist(),'state_runs':states,'state_mask':pack(state),'alerts_inside_state':evidence,'prefix_checks':prefix,'right_censored_last_state':bool(state[-1]),'evaluation':'conditional discovery only; source prefixes read for calculation; other periods not scored'}
    return payload,results
def audit_one(raw,rows):
    states=raw['state_runs'];n=len(raw['timestamps']);state=unpack(raw['state_mask'],n);seen=set()
    # Independent per-bar loop; does not call production score/summarize.
    for row in rows:
        ident=row['candidate_id'];assert ident not in seen;seen.add(ident);a=unpack(raw['alerts_inside_state'][ident],n);assert not np.any(a&~state)
        counts=[0]*len(states);first={}
        for i in np.flatnonzero(a):
            match=[j for j,(start,end) in enumerate(states) if start<=i<=end];assert len(match)==1
            j=match[0];counts[j]+=1;first.setdefault(j,int(i))
        assert row['alerts']==sum(counts) and row['caught']==len(first) and row['missed']==len(states)-len(first)
        assert row['repeated']==sum(max(0,k-1) for k in counts)
        assert row['first_indices']==list(first.values())
        assert row['delays']==[i-states[j][0] for j,i in first.items()]
        assert row['coverage']==(len(first)/len(states) if states else None)
        assert row['states']==len(states) and row['state_bars']==int(state.sum())
    assert seen==set(raw['alerts_inside_state']);return len(rows)
def report(out,manifest,allrows):
    nm='غير مقاس — خارج هذه المرحلة';lines=['# تقرير التقاط حالة الاختراق الصاعد — BTCUSDT Spot','',
    '1. التجربة: نسخ مسجلة على شموع15دقيقة داخل حالة صعود واحدة فقط.',f'2. الصافي بعد التكلفة: {nm}.',f'3. الصفقات ونصيب الصفقة: {nm}.',f'4. عامل الربح: {nm}.',
    '5. الفترة العمياء: غير مقاسة؛ هذه شهور تاريخية سبق فحصها.',f'6. مقابل الاحتفاظ: {nm}.','7. الحالة: قياس وصفي ينتظر مراجعة القائد؛ لا اعتماد.','8. التالي: تدقيق القائد للأدلة الخام قبل أي مرحلة أخرى.','',
    '## سلامة القياس','التدقيق يعيد عد كل صف من إشاراته الخام. نتائج الفحص فيaudit.json. نجاح الجاهزية الاصطناعية لا يثبت جودة سوقية.','',
    '## 1 — هوية التجربة','| البند | القيمة |','|---|---|','| العملة | BTCUSDT Spot |','| الفريم | 15 دقيقة |','| التعلم | اكتشاف وصفي في الشهور المسجلة |','| الامتحان | غير مقاس |','| العمياء | غير مقاسة |',f'| التكلفة والانزلاق | {nm} |','',
    '## 2 — إحصاءات المال','| المقياس | المعنى | الصيغة | القيمة |','|---|---|---|---|']
    for title,meaning,formula in [('الصافي','ما يبقى بعد التكلفة','الربح−الخسارة−التكلفة'),('عامل الربح','ربح لكل دولار خسارة','الربح الإجمالي÷الخسارة الإجمالية'),('نصيب الصفقة','حصة الأمر','الصافي÷عدد الصفقات'),('توقع الصفقة','المتوسط المالي','احتمال الفوز×متوسط الربح−احتمال الخسارة×متوسط الخسارة'),('الرسوم','تكلفة التنفيذ','عدد الصفقات×التكلفة')]:lines.append(f'| {title} | {meaning} | {formula} | {nm} |')
    lines+=['','## 3 — إحصاءات الصفقات','| المقياس | القيمة |','|---|---|']
    for x in ['عدد الصفقات','نسبة الفوز','متوسط الرابحة','متوسط الخاسرة','نسبة متوسط الربح إلى الخسارة','أطول سلسلة خسائر','متوسط الاحتفاظ']:lines.append(f'| {x} | {nm} |')
    lines+=['','## 4 — المخاطر والتراجع','| المقياس | القيمة | مقابل الخط الملزم |','|---|---|---|']
    for x in ['أقصى تراجع','مدة التراجع','أسوأ يوم','التعرض']:lines.append(f'| {x} | {nm} | خارج مرحلة الإشارات |')
    lines+=['','## 5 — الجوار والثبات','| البند | القيمة |','|---|---|','| الجوار ±20% | غير مقاس؛ لا إعدادات مضافة خارج سجل الدفعة |','| الثبات بين الشهور | جميع النسخ وجميع الشهور فيresults.csv.gz؛ لا اختيار فائز آلي |','',
    '## 6 — الفترات والاحتفاظ','| الفترة | الصافي | الصفقات | عامل الربح | ملاحظة |','|---|---|---|---|---|']
    for x in ['التعلم','الامتحان','العمياء','الاحتفاظ']:lines.append(f'| {x} | {nm} | {nm} | {nm} | لا تجربة مالية |')
    lines+=['','## 7 — شروط الاعتماد','| الشرط | المطلوب | المقاس | الحكم |','|---|---|---|---|']
    for x in ['عامل الربح','عدد الصفقات','الثبات الإحصائي المالي','الجوار','نجاة العمياء','تجاوز الاحتفاظ']:lines.append(f'| {x} | خارج هذه المرحلة | {nm} | لا اعتماد |')
    lines+=['','## نتائج الحالة','| الشهر | حالات الحالة | شموع الحالة | صفوف النتائج |','|---|---|---|---|']
    for m in manifest['months']:
        sub=[r for r in allrows if r['month']==m];r=sub[0];lines.append(f"| {m} | {r['states']} حالة | {r['state_bars']} شمعة | {len(sub)} صفًا |")
    lines+=['','## المثبت وغير المثبت','المثبت: عد الإشارات والتغطية والتأخير داخل التعريف المسجل، بعد نجاح التدقيق. غير المثبت: الدقة العامة، الإشارات الكاذبة خارج الحالة، جودة نظام يشتغل طوال الوقت، الربحية وأفضلية مستقبلية. لا نسبة نجاح مفروضة ولا ترتيب فائز بناءً على أعلى متوسط.','',
    'هذه الدفعة جزء من الفهرس؛ coverage_scope.json يثبت ما شملته وما بقي غير مقاس. الإشارات المركبة الموروثة تحمل وصفها ولا تسمى مؤشرات مستقلة. النسخ ذات الصفر باقية.','',
    'فواصل Wilson وصفية وتفترض استقلال الحالات؛ day_bootstrap95 يعيد أخذ أيام الحالات ببذرة ثابتة، ويظل مشروطًا بهذه الشهور. لا اختبار دلالة ولا ادعاء تفوق مصحح لبحث واسع.','',
    '## بطاقة الحكم والتوثيق','الحكم المستقل: ينتظر القائد. التنفيذ لا يتبنى ولا يختار بديلًا من التحقق. الأرباح: غير مقاسة.','',
    '## قاموس المصطلحات','| المصطلح | المعنى/الصيغة |','|---|---|','| التغطية | حالات التقطتها إشارة واحدة على الأقل ÷ جميع حالات التعريف |','| التأخير | عدد الشموع من أول شمعة للحالة إلى أول إشارة داخلها |','| الإشارات المكررة | إشارات الحالة بعد أول إشارة للنسخة نفسها |','| الحركة المتبقية الوصفية | أعلى إغلاق من الإشارة إلى نهاية الحالة ÷ إغلاق الإشارة −1؛ ليست صفقة |','',
    '## قاموس التعبيرات','| التعبير | العبارة المستخدمة |','|---|---|','| factory | قائمة الأفكار |','| plateau | ثبات الإعدادات المجاورة |','| lane | المهمة البحثية |','',
    '## أوامر إعادة الاشتقاق','من مجلد الحزمة: python specialist.py audit --out OUTPUT. كل صف فيresults.csv.gz يعاد عده منMONTH.raw.json.gz. راجعpaper.md لتعريف الحالة وحدودها.']
    atomic(out/'REPORT_AR.md',('\n'.join(lines)+'\n').encode())
def audit(out):
    out=Path(out);manifest=json.loads((out/'checkpoint.json').read_text());allrows=[];count=0
    assert manifest['fingerprint']==fingerprint(manifest['fixture']),'audit source/settings/runtime fingerprint changed'
    for item in manifest['parts']:
        for name in ['raw','rows']:assert sha(out/item[name])==item[name+'_sha256']
        raw=json.loads(gzip.decompress((out/item['raw']).read_bytes()));rows=json.loads(gzip.decompress((out/item['rows']).read_bytes()));count+=audit_one(raw,rows);allrows.extend(rows)
    assert len(manifest['parts'])==len(manifest['months']),'incomplete checkpoint'
    assert count==len(manifest['months'])*(len(grid())+3)
    jsonout(out/'audit.json',{'status':'PASS','independent_scalar_count_rows':count,'months':len(manifest['months']),'zero_signal_rows_retained':True,'full_stream_precision':'not measured','market_status':'SYNTHETIC_ONLY' if manifest['fixture'] else 'DISCOVERY_LEAD_REVIEW_PENDING'})
    buf=io.StringIO();fields=['candidate_id','month','states','state_bars','alerts','caught','missed','repeated','coverage','median_delay_bars','median_remaining_close_gain_pct','matched_count_random_state_coverage','precision'];w=csv.DictWriter(buf,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(allrows);atomic(out/'results.csv.gz',gzip.compress(buf.getvalue().encode(),mtime=0));report(out,manifest,allrows)
    return count
def run(out,synthetic=False,stop_after=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);g=grid();inputs=json.loads((ROOT/'inputs.json').read_text());months=['2024-01'] if synthetic else MONTHS
    digest=fingerprint(synthetic)
    checkpoint=out/'checkpoint.json';old=json.loads(checkpoint.read_text()) if checkpoint.exists() else None
    if old:assert old['fingerprint']==digest,'changed package or source'
    manifest={'fingerprint':digest,'months':months,'fixture':synthetic,'parts':[]}
    for m in months:
        rawname=m+'.raw.json.gz';rowname=m+'.rows.json.gz'
        previous=next((x for x in old['parts'] if x['month']==m),None) if old else None
        if previous:
            for k in ['raw','rows']:assert sha(out/previous[k])==previous[k+'_sha256']
            manifest['parts'].append(previous)
        else:
            if synthetic:d=fixture()
            else:
                item=next(x for x in inputs if x['month']==m);path=ROOT/item['local_path'];assert sha(path)==item['sha256'];d=load_data(path)
            raw,rows=measure_one(d,m,g);audit_one(raw,rows)
            atomic(out/rawname,gzip.compress(encode(raw),mtime=0));atomic(out/rowname,gzip.compress(encode(rows),mtime=0));manifest['parts'].append({'month':m,'raw':rawname,'raw_sha256':sha(out/rawname),'rows':rowname,'rows_sha256':sha(out/rowname)})
        # Checkpoint is the only mutable generated state; atomic replace and lease fingerprint.
        b=encode(manifest)
        if workspace_bytes(os.environ.get('NOVA_WORKSPACE',ROOT.parent))+len(b)>125000000:raise RuntimeError('125 MB workspace limit before checkpoint')
        tmp=checkpoint.with_suffix('.pending');tmp.write_bytes(b);os.replace(tmp,checkpoint)
        print('CHECKPOINT',m,flush=True)
        if stop_after and len(manifest['parts'])>=stop_after:return 'CHECKPOINT_ONLY'
    audit(out);return 'SYNTHETIC_ONLY' if synthetic else 'DISCOVERY_LEAD_REVIEW_PENDING'
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['fixture','measure','audit']);p.add_argument('--out',required=True);p.add_argument('--stop-after',type=int);a=p.parse_args()
    Path(a.out).mkdir(parents=True,exist_ok=True)
    lock=(Path(a.out)/'.worker.lock').open('a+')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise SystemExit('another worker holds this output; poll it, do not restart')
    started=time.monotonic();status=audit(a.out) if a.mode=='audit' else run(a.out,a.mode=='fixture',a.stop_after)
    print(json.dumps({'status':status,'compute_seconds':time.monotonic()-started}))
