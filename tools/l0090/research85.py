"""One registered L0085 discovery experiment; no order, money or fill engine."""
from pathlib import Path
import csv,gzip,hashlib,io,itertools,json,math,os,time,heapq,random
import numpy as np
import indicators84 as I
import signals85 as S
ROOT=Path(__file__).resolve().parent
ASSETS=['BTCUSDT','ETHUSDT','SOLUSDT']; MODES=['AND0','AND2','OR0']; BATCH=20000

def write_json(p,x):
    p=Path(p);b=(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();atomic(p,b)
def atomic(p,b):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.pending')
    workspace=os.environ.get('NOVA85_WORKSPACE')
    if workspace:
        used=sum(q.stat().st_size for q in Path(workspace).rglob('*') if q.is_file() and not q.is_symlink())
        if used+len(b)>125000000:raise RuntimeError('Workspace cap before atomic write: '+str(used)+' + '+str(len(b)))
    with open(tmp,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
    os.replace(tmp,p)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pack(a):return sum(1<<int(i) for i in np.flatnonzero(a))
def bits(x):
    while x:
        k=x&-x;yield k.bit_length()-1;x-=k

def load_market():
    out={}
    for m in json.loads((ROOT/'inputs.json').read_text()):
        p=ROOT/m['file'];assert sha(p)==m['sha256'],p.name
        rows=list(csv.DictReader(p.open()));assert len(rows)==m['rows']
        from datetime import datetime
        times=[datetime.fromisoformat(x['dt'].replace('Z','+00:00')).timestamp() for x in rows]
        assert all(b-a==14400 for a,b in zip(times,times[1:]))
        d={k:np.array([float(x[v]) for x in rows]) for k,v in zip(['o','h','l','c','v','tbv'],['open','high','low','close','volume','taker_buy_volume'])};d['dt']=[x['dt'] for x in rows]
        assert all(np.isfinite(d[k]).all() for k in ['o','h','l','c','v','tbv'])
        assert ((d['l']<=np.minimum(d['o'],d['c']))&(d['h']>=np.maximum(d['o'],d['c']))&(d['h']>=d['l'])&(d['l']>0)&(d['v']>0)&(d['tbv']>=0)&(d['tbv']<=d['v'])).all()
        out[m['asset']]=d
    assert list(out)==ASSETS
    return out

def fixture():
    out={}
    for z,sym in enumerate(ASSETS):
        n=420;x=np.arange(n);rng=np.random.default_rng(850+z)
        c=100+5*np.sin(x/(8+z))+.3*np.sin(x/2)+rng.normal(0,.08,n);o=np.r_[c[0],c[:-1]];h=np.maximum(c,o)+.12;l=np.minimum(c,o)-.12;v=100+20*np.sin(x/3)+rng.uniform(0,30,n)
        out[sym]={'o':o,'h':h,'l':l,'c':c,'v':v,'tbv':v*(.5+.1*np.sin(x/5)),'dt':['fixture-'+str(i) for i in range(n)]}
    return out

def labels(d,start,end):
    """Evaluation-only centered pivots; disjoint onset episodes at least 25 bars apart."""
    h,l,c=d['h'],d['l'],d['c'];atr=I.wilder_atr(h,l,c,14);events=[];last=-1000
    # Uniform scored decision bars start+5..end-25 inclusive. Onset matching windows fully inside these.
    for t in range(start+7,end-26):
        if t-last<25 or not np.isfinite(atr[t]) or atr[t]<=0:continue
        if int(np.argmin(l[t-5:t+6]))!=5:continue # first/earliest tied minimum only
        upper=c[t]+2*atr[t];lower=c[t]-atr[t];hit=None
        for k in range(t+1,t+25):
            if l[k]<=lower:break # adverse wins a same-bar tie
            if h[k]>=upper:hit=k;break
        if hit is not None:
            events.append({'onset':t,'hit':hit,'atr':float(atr[t]),'close':float(c[t]),'window':list(range(t-2,t+3))});last=t
    return events

def labels_reference(d,start,end):
    # Separate scalar reference, no call to labels or its matching routine.
    h,l,c=[list(map(float,d[k])) for k in ['h','l','c']];a=[];prev=None
    for i in range(len(c)):
        tr=max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) if i else h[i]-l[i]
        prev=tr if prev is None else prev*13/14+tr/14;a.append(prev if i>=13 else float('nan'))
    found=[];last=-1000
    for t in range(start+7,end-26):
        if t-last<25:continue
        center=min(range(t-5,t+6),key=lambda k:l[k])
        if center!=t or not math.isfinite(a[t]) or a[t]<=0:continue
        up=next((k for k in range(t+1,t+25) if h[k]>=c[t]+2*a[t]),None)
        down=next((k for k in range(t+1,t+25) if l[k]<=c[t]-a[t]),None)
        if up is not None and (down is None or up<down):found.append((t,up));last=t
    return found

def combine(a,b,mode,fullmask):
    if mode=='S':x=a
    elif mode=='AND0':x=a&b
    elif mode=='OR0':x=a|b
    elif mode=='AND2':x=(a|(a<<1)|(a<<2))&(b|(b<<1)|(b<<2))
    else:raise ValueError(mode)
    return (x & ~(x<<1))&fullmask # one alert at each false->true transition

def candidates(grid):
    k=0
    for i in range(len(grid)):yield k,i,-1,'S';k+=1
    for i,j in itertools.combinations(range(len(grid)),2):
        for mode in MODES:yield k,i,j,mode;k+=1

def score(x,events):
    count=x.bit_count();tp=0;lag=0
    for e in events:
        common=x&e['mask']
        if common:tp+=1;lag+=(common&-common).bit_length()-1-e['onset']
    return count,tp,lag

def score_reference(x,events):
    alerts=list(bits(x));claimed=set();lags=[]
    for i in alerts:
        for j,e in enumerate(events):
            if j not in claimed and abs(i-e['onset'])<=2:
                claimed.add(j);lags.append(i-e['onset']);break
    return len(alerts),len(claimed),sum(lags)

def metric(ns,tp,ne):
    p=tp/ns if ns else 0.;r=tp/ne if ne else 0.;f=2*tp/(ns+ne) if ns+ne else 0.
    return {'signals':ns,'matched_events':tp,'false_or_duplicate':ns-tp,'events':ne,'precision':p,'recall':r,'f1':f}

def ready_inputs(panels,synthetic=False):
    grid=S.catalogue();raw={'grid':grid,'assets':{},'synthetic':synthetic,'budget':len(grid)+3*math.comb(len(grid),2)}
    for sym,d in panels.items():
        start=260 if synthetic else d['dt'].index('2025-01-01T00:00:00Z');end=len(d['c']);masks=S.build(d,grid)
        checks=0
        for cut in ([300,355] if synthetic else [1200,1440]):
            pre=S.build({k:v[:cut] for k,v in d.items()},grid)
            for name,a in masks.items():assert np.array_equal(pre[name],a[:cut]),('causality',sym,name,cut);checks+=1
        ev=labels(d,start,end);assert [(e['onset'],e['hit']) for e in ev]==labels_reference(d,start,end)
        valid=sum(1<<i for i in range(start+5,end-24))
        for e in ev:e['mask']=sum(1<<i for i in e['window'])
        raw['assets'][sym]={'start':start,'end':end,'times':d['dt'],'valid':hex(valid),'events':ev,'masks':[hex(pack(masks[q['id']])) for q in grid],'prefix_checks':checks}
    return raw

def inflate(raw):
    data=[]
    for a in raw['assets'].values():data.append((int(a['valid'],16),[int(x,16) for x in a['masks']],a['events']))
    return data

def row_for(key,data,reference=False):
    k,i,j,mode=key;fields=[k,i,j,mode]
    for valid,masks,ev in data:
        if reference:
            # Independent logical-array mode reconstruction, including edge conversion.
            n=valid.bit_length();a=set(bits(masks[i]));b=set(bits(masks[j])) if j>=0 else set();truth=[]
            for t in range(n):
                if mode=='S':v=t in a
                elif mode=='AND0':v=t in a and t in b
                elif mode=='OR0':v=t in a or t in b
                else:v=any(t-z in a for z in range(3)) and any(t-z in b for z in range(3))
                truth.append(v)
            x=sum(1<<t for t,v in enumerate(truth) if v and (t==0 or not truth[t-1]) and (valid>>t)&1)
            value=score_reference(x,ev)
        else:value=score(combine(masks[i],masks[j] if j>=0 else 0,mode,valid),ev)
        fields.extend(value)
    return fields
HEADER=['candidate','a','b','mode']+[s+'_'+n for s in ASSETS for n in ['signals','matched','lag_sum']]

def batch_bytes(rows):
    b=io.StringIO(newline='');w=csv.writer(b,lineterminator='\n');w.writerow(HEADER);w.writerows(rows);return gzip.compress(b.getvalue().encode(),mtime=0)

def run(out,synthetic=False,stop_after=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);panels=fixture() if synthetic else load_market()
    raw=ready_inputs(panels,synthetic);encoded=json.dumps(raw,sort_keys=True).encode();digest=hashlib.sha256(encoded).hexdigest()
    saved=out/'raw_signals.json.gz'
    if saved.exists():assert gzip.decompress(saved.read_bytes())==encoded,'changed raw evidence'
    else:atomic(saved,gzip.compress(encoded,mtime=0))
    data=inflate(raw);keys=list(candidates(raw['grid']));manifest={'raw_sha256':sha(saved),'budget':len(keys),'synthetic':synthetic,'parts':[]}
    old=json.loads((out/'checkpoint.json').read_text()) if (out/'checkpoint.json').exists() else None
    if old:assert old['raw_sha256']==manifest['raw_sha256'] and old['budget']==len(keys)
    for offset in range(0,len(keys),BATCH):
        name='scores-%05d.csv.gz'%(offset//BATCH);p=out/name;rows=[row_for(x,data) for x in keys[offset:offset+BATCH]];b=batch_bytes(rows)
        if p.exists():assert p.read_bytes()==b,('changed/incomplete partition',name)
        else:atomic(p,b)
        rec={'file':name,'first':offset,'rows':len(rows),'bytes':len(b),'sha256':sha(p)};manifest['parts'].append(rec);write_json(out/'checkpoint.json',manifest)
        print('SCORED',offset+len(rows),'/',len(keys),flush=True)
        if stop_after is not None and len(manifest['parts'])>=stop_after:return {'status':'INTERRUPTED_FIXTURE','completed':offset+len(rows)}
    audit(out);report(out);return {'status':'DISCOVERY_COMPLETE_LEAD_REVIEW_PENDING','budget':len(keys),'raw_digest':digest}

def audit(out):
    out=Path(out);m=json.loads((out/'checkpoint.json').read_text());assert sha(out/'raw_signals.json.gz')==m['raw_sha256'];raw=json.loads(gzip.decompress((out/'raw_signals.json.gz').read_bytes()));data=inflate(raw);keys=list(candidates(raw['grid']));assert len(keys)==m['budget'];seen=0;reference_rows=0
    # All rows independently reconciled to alert/event raw evidence; sample modes additionally rebuilt scalar.
    for rec in m['parts']:
        p=out/rec['file'];assert sha(p)==rec['sha256'] and p.stat().st_size==rec['bytes']
        rows=list(csv.reader(io.StringIO(gzip.decompress(p.read_bytes()).decode())));assert rows.pop(0)==HEADER;assert len(rows)==rec['rows'] and rec['first']==seen
        for row in rows:
            got=[int(v) if j!=3 else v for j,v in enumerate(row)];key=keys[seen];assert got[:4]==list(key)
            expected=[*key]
            for valid,masks,events in data:
                x=combine(masks[key[1]],masks[key[2]] if key[2]>=0 else 0,key[3],valid)
                # Independent one-to-one matching counts, without production score().
                expected.extend(score_reference(x,events))
            assert got==expected,('audit row',seen)
            if seen%10000==0 or seen==len(keys)-1:assert got==row_for(key,data,True);reference_rows+=1
            seen+=1
        print('AUDITED',seen,'/',len(keys),flush=True)
    assert seen==len(keys),'missing candidates'
    write_json(out/'audit.json',{'status':'PASS','rows':seen,'independent_matching_all_rows':True,'scalar_mode_reference_rows':reference_rows,'zero_signal_rows_retained':True,'raw_sha256':m['raw_sha256'],'source_status':'synthetic' if raw['synthetic'] else 'historical_discovery'})

def read_rows(out):
    m=json.loads((out/'checkpoint.json').read_text())
    for rec in m['parts']:
        for row in csv.DictReader(io.StringIO(gzip.decompress((out/rec['file']).read_bytes()).decode())):
            yield {k:(v if k=='mode' else int(v)) for k,v in row.items()}

def detail(raw,row):
    per=[]
    for sym,a in raw['assets'].items():
        x=metric(row[sym+'_signals'],row[sym+'_matched'],len(a['events']));x['asset']=sym;per.append(x)
    m=metric(sum(x['signals'] for x in per),sum(x['matched_events'] for x in per),sum(x['events'] for x in per))
    m.update(row);m['macro_f1']=sum(x['f1'] for x in per)/len(per);m['per_asset']=per
    m['eligible']=m['signals']>=15 and m['matched_events']>=6 and all(x['signals']>=3 and x['events']>=3 for x in per)
    m['rule']=[raw['grid'][row['a']]]+([raw['grid'][row['b']]] if row['b']>=0 else []);return m

def report(out):
    out=Path(out);raw=json.loads(gzip.decompress((out/'raw_signals.json.gz').read_bytes()));best=[];qualified=[];pairs=[];qualified_pairs=[];singles=[];best_family={};byasset={s:[] for s in ASSETS};count=0
    def keep(heap,x,key):
        val=(key,-x['candidate'],x)
        if len(heap)<20:heapq.heappush(heap,val)
        elif val[:2]>heap[0][:2]:heapq.heapreplace(heap,val)
    for row in read_rows(out):
        d=detail(raw,row);count+=1;keep(best,d,d['macro_f1'])
        if d['eligible']:keep(qualified,d,d['macro_f1'])
        if row['mode']!='S':
            keep(pairs,d,d['macro_f1'])
            if d['eligible']:keep(qualified_pairs,d,d['macro_f1'])
        if row['mode']=='S':
            singles.append(d);fam=d['rule'][0]['family']
            if fam not in best_family or (d['macro_f1'],-d['candidate'])>(best_family[fam]['macro_f1'],-best_family[fam]['candidate']):best_family[fam]=d
        for s,x in zip(ASSETS,d['per_asset']):keep(byasset[s],d,x['f1'])
    order=lambda h:[x[2] for x in sorted(h,reverse=True)]
    top=order(qualified) if qualified else order(best);write_json(out/'ranking.json',{'all_top20':order(best),'eligible_top20':order(qualified),'pair_top20':order(pairs),'eligible_pair_top20':order(qualified_pairs),'best_by_family':best_family,'best_by_asset':{s:order(h) for s,h in byasset.items()}})
    selected=(order(qualified_pairs) if qualified_pairs else order(pairs))[:10];
    top=list({d['candidate']:d for d in top[:10]+selected}.values());write_json(out/'selection.json',{'status':'PROVISIONAL_DISCOVERY_ONLY' if qualified_pairs else 'INSUFFICIENT_SAMPLE','frozen_candidate_ids':[x['candidate'] for x in selected],'rules':selected,'validation_read':False,'future_claim':False})
    data=inflate(raw);controls=[];alerts=[];months=[];panels=fixture() if raw['synthetic'] else load_market()
    for d in top:
        for sym,(valid,masks,events) in zip(ASSETS,data):
            a=raw['assets'][sym];panel=panels[sym];atr=I.wilder_atr(panel['h'],panel['l'],panel['c'],14);x=combine(masks[d['a']],masks[d['b']] if d['b']>=0 else 0,d['mode'],valid);claimed=set()
            for bar in bits(x):
                match=next((j for j,e in enumerate(events) if j not in claimed and abs(bar-e['onset'])<=2),None)
                if match is not None:claimed.add(match)
                alerts.append({'candidate':d['candidate'],'asset':sym,'bar':bar,'time':a['times'][bar],'event':match,'onset':events[match]['onset'] if match is not None else None,'lag':bar-events[match]['onset'] if match is not None else None,'mae_atr_24':float(min(0,np.min(panel['l'][bar+1:bar+25])-panel['c'][bar])/atr[bar]),'mfe_atr_24':float(max(0,np.max(panel['h'][bar+1:bar+25])-panel['c'][bar])/atr[bar])})
            indices=list(bits(valid));n=len(indices);base=indices[0];local=x>>base;rng=random.Random(85);shifts=rng.sample(range(25,n-24),min(19,max(0,n-49)))
            for shift in shifts:
                moved=(((local<<shift)|(local>>(n-shift)))&((1<<n)-1))<<base;ns,tp,lag=score(moved,events);controls.append({'candidate':d['candidate'],'asset':sym,'shift':shift,**metric(ns,tp,len(events))})
            for month in sorted({a['times'][i][:7] for i in indices}):
                mask=sum(1<<i for i in indices if a['times'][i][:7]==month)
                # Month counts assigned to alert month and event-onset month separately; cross-month matches retained.
                aa=[z for z in alerts if z['candidate']==d['candidate'] and z['asset']==sym and z['time'][:7]==month]
                months.append({'candidate':d['candidate'],'asset':sym,'month':month,'signals':len(aa),'matched_alerts':sum(z['event'] is not None for z in aa),'onsets':sum(a['times'][e['onset']][:7]==month for e in events)})
    baselines=[]
    for sym,(valid,_,events) in zip(ASSETS,data):
        for name,x in [('NONE',0),('EVERY_BAR',valid),('EVERY_5_BARS',sum(1<<i for i in bits(valid) if (i-(valid&-valid).bit_length()+1)%5==0))]:
            ns,tp,_=score(x,events);baselines.append({'asset':sym,'baseline':name,**metric(ns,tp,len(events))})
    write_json(out/'controls.json',{'baselines':baselines,'shift_controls_top20':controls,'inferential_p_values':'NOT MEASURED; selected-candidate shifts are descriptive, not multiplicity-adjusted'})
    write_json(out/'alerts_top20.json',alerts);
    diagnostics=[]
    for d in top:
        for sym in ASSETS:
            aa=[v for v in alerts if v['candidate']==d['candidate'] and v['asset']==sym];lags=[v['lag'] for v in aa if v['lag'] is not None];ns=len(aa);tp=len(lags);z=1.959963984540054
            if ns:
                phat=tp/ns;den=1+z*z/ns;center=(phat+z*z/(2*ns))/den;half=z*math.sqrt(phat*(1-phat)/ns+z*z/(4*ns*ns))/den;wilson=[center-half,center+half]
            else:wilson=None
            diagnostics.append({'candidate':d['candidate'],'asset':sym,'signals':ns,'precision_wilson95_descriptive':wilson,'lag_median_bars':float(np.median(lags)) if lags else None,'mae_median_atr_24':float(np.median([v['mae_atr_24'] for v in aa])) if aa else None,'mfe_median_atr_24':float(np.median([v['mfe_atr_24'] for v in aa])) if aa else None,'interval_limit':'Not corrected for serial dependence or search selection'})
    write_json(out/'diagnostics_top20.json',diagnostics);write_json(out/'months_top20.json',months)
    # Numeric comparisons to single parents; no claims of unmeasured financial performance.
    parents={x['candidate']:x for x in singles};comparison=[]
    for d in top:
        comparison.append({'candidate':d['candidate'],'macro_f1':d['macro_f1'],'best_parent_macro_f1':max(parents[k]['macro_f1'] for k in [d['a'],d['b']] if k>=0),'difference':d['macro_f1']-max(parents[k]['macro_f1'] for k in [d['a'],d['b']] if k>=0)})
    write_json(out/'parent_comparison.json',comparison)
    lines=['# L0085 — نتائج اكتشاف إشارات بداية الصعود','',
        '1. اختبار الإشارات والمزائج على BTC وETH وSOL، أربع ساعات، يناير–مارس 2025.' if not raw['synthetic'] else '1. اختبار اصطناعي للمسار فقط؛ لا نتيجة سوق.',
        '2. صافي المال: not measured — مستبعد بأمر المالك.','3. الصفقات: not measured؛ العينة إشارات وأحداث صعود.',
        '4. معامل الربح: not measured.','5. اختبار أعمى: not measured؛ هذه فترة بحث تاريخية منظور سابقًا.',
        '6. الشراء والاحتفاظ: not measured.','7. الحكم: Defer — ترتيب اكتشافي، لا اعتماد تداول.',
        '8. التالي: Lead يعيد الحساب من الخام ويدقق المرشحين قبل ورقة التحقق.','',
        '## 1. الهوية','| البند | القيمة |','|---|---|',f'| الحالات | {count} |','| المصدر | scope.json وinputs.json |','| الموضوع | بداية الصعود بلا محرك صفقات |',
        '## 2. المال','| الحقل | القيمة |','|---|---|','| الصافي والتكاليف والتوقع ومعامل الربح | not measured |',
        '## 3. الإشارات','| المرشح وتعريفه | إشارات | أحداث ملتقطة | الدقة | الاسترجاع | متوسط F1 للعملات |','|---|---:|---:|---:|---:|---:|']
    for d in top:lines.append(f"| {d['candidate']}: {d['mode']} / {' + '.join(q['id'] for q in d['rule'])} | {d['signals']} | {d['matched_events']} | {d['precision']:.6f} | {d['recall']:.6f} | {d['macro_f1']:.6f} |")
    lines+=['## 4. المخاطر','| الحقل | القيمة |','|---|---|','| هبوط رأس المال والتعرض | not measured |','| التنبيهات الخاطئة أو المكررة | signals − matched_events؛ الجداول الخام |',
        '## 5. الجوار','| الحقل | القيمة |','|---|---|','| جميع الإعدادات والمزائج | scores-*.csv.gz |','| حكم جوار ±20% | not measured؛ لا اعتماد من قمة منفردة |',
        '## 6. الفترات','| الفترة | الحالة |','|---|---|','| البحث | الجداول الحالية |','| التفصيل الشهري للمتصدرين | months_top20.json |','| التحقق المحجوز | not measured |','| العمياء والاحتفاظ | not measured |',
        '## 7. شروط الاعتماد','| الشرط | الحالة |','|---|---|','| اكتمال البحث والتدقيق | audit.json |','| حجم عينة مؤهل للترتيب الأولي | selection.json |','| صحة خارج فترة البحث والربحية والاستقرار | not measured |',
        '## قاموس المصطلحات','| المصطلح | المعنى |','|---|---|','| Precision | حدث واحد صحيح لكل تنبيه، دون مكافأة التكرار |','| Recall | الأحداث الملتقطة ÷ كل أحداث الصعود |','| F1 | 2 × الأحداث الملتقطة ÷ (الإشارات + الأحداث) |','| Macro F1 | متوسط F1 للعملات بالتساوي |',
        '## قاموس الأسماء','| الاسم | المعنى |','|---|---|','| AND0 | تحقق الطرفين الآن |','| AND2 | تحقق كل طرف خلال الحالية والشمعتين السابقتين |','| OR0 | تحقق أحد الطرفين الآن |','| onset | شمعة القاع المرجعية، تُعرف لاحقًا للتقييم فقط |',
        '', 'لا توصية تداول. أقوى نتيجة في هذا البحث لا تثبت أنها أقوى مزيج خارج الشبكة أو خارج هذه الفترة. لا قيم احتمالية مصححة؛ البحث استكشافي.',
        '', 'إعادة التدقيق والتقرير: python research85.py audit --out PATH','']
    atomic(out/'REPORT.md','\n'.join(lines).encode());write_json(out/'delivery.json',{'status':'DISCOVERY_COMPLETE_LEAD_REVIEW_PENDING','rows':count,'synthetic':raw['synthetic'],'adoption':'NOT AUTHORISED','validation':'NOT RUN'})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['synthetic','measure','audit']);p.add_argument('--out',required=True);p.add_argument('--stop-after',type=int);a=p.parse_args()
    if a.mode=='audit':audit(a.out);report(a.out)
    else:print(json.dumps(run(a.out,a.mode=='synthetic',a.stop_after)))
