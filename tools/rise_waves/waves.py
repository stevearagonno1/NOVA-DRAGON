"""Closed-bar SOL pilot. Standard library only; original bot is never imported."""
import csv,json,math,gzip,hashlib,pathlib,time,argparse,statistics
ROOT=pathlib.Path(__file__).resolve().parent
FRAMES=(15,60)
RULES=('EMA_RECLAIM','EMA_RECLAIM_VOL','RANGE_BREAK','RANGE_BREAK_VOL','VWAP_RECLAIM','VWAP_RECLAIM_VOL','BOT_RAW','BOT_CONTEXT','CONTEXT_EDGE','CONTEXT_DAILY')
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def aggregate(raw,m):
    out=[]
    for start in range(0,len(raw),m):
        ix=raw[start:start+m]
        if len(ix)!=m:continue
        assert ix[0][0]%(m*60)==0
        out.append([ix[0][0],ix[0][1],max(x[2] for x in ix),min(x[3] for x in ix),ix[-1][4],sum(x[5] for x in ix)])
    return out
def ema(c,n):
    out=[];v=c[0]
    for x in c:v+=2/(n+1)*(x-v);out.append(v)
    return out
def ema_sma_seed(c,n):
    out=[None]*len(c)
    if len(c)<n:return out
    out[n-1]=sum(c[:n])/n
    for i in range(n,len(c)):out[i]=2/(n+1)*c[i]+(1-2/(n+1))*out[i-1]
    return out
def atr(b,n=14):
    tr=[b[0][2]-b[0][3]]+[max(x[2]-x[3],abs(x[2]-b[i-1][4]),abs(x[3]-b[i-1][4])) for i,x in enumerate(b[1:],1)]
    out=[None]*len(b)
    if len(b)<n:return out
    out[n-1]=sum(tr[:n])/n
    for i in range(n,len(b)):out[i]=(out[i-1]*(n-1)+tr[i])/n
    return out
def rsi(c,n=14,flat_value=50):
    out=[None]*len(c)
    if len(c)<=n:return out
    g=sum(max(c[i]-c[i-1],0) for i in range(1,n+1))/n;l=sum(max(c[i-1]-c[i],0) for i in range(1,n+1))/n
    def val():return flat_value if g==l==0 else 100 if l==0 else 100-100/(1+g/l)
    out[n]=val()
    for i in range(n+1,len(c)):
        d=c[i]-c[i-1];g=(g*(n-1)+max(d,0))/n;l=(l*(n-1)+max(-d,0))/n;out[i]=val()
    return out

def signals(raw,m,reference=False):
    b=aggregate(raw,m);context=aggregate(raw,60 if m==15 else 240);hour=aggregate(raw,60)
    c=[x[4] for x in b];e=ema(c,20);rs=rsi(c,flat_value=100);mac=[None if x is None or y is None else x-y for x,y in zip(ema_sma_seed(c,12),ema_sma_seed(c,26))]
    ctxc=[x[4] for x in context];ce20=ema(ctxc,20);ce50=ema(ctxc,50);ha=atr(hour)
    out={q:[] for q in RULES};prev={q:False for q in RULES};last={q:-10**18 for q in RULES}
    details={};cv=pv=0;day=None
    for i,x in enumerate(b):
        at=x[0]+m*60;d=x[0]//86400
        if d!=day:day=d;cv=pv=0
        oldcv,oldpv=cv,pv
        cv+=x[5];pv+=(x[2]+x[3]+x[4])/3*x[5];vwap=pv/cv if cv else None
        j=at//((60 if m==15 else 240)*60)-context[0][0]//((60 if m==15 else 240)*60)-1
        h=at//3600-hour[0][0]//3600-1
        context_ok=j>=50 and ce20[j]>ce50[j] and ce20[j]>ce20[j-1]
        rv=x[5]/(sum(z[5] for z in b[i-20:i])/20) if i>=20 and sum(z[5] for z in b[i-20:i])>0 else 0
        volume=rv>=1.5
        valid=i>=50 and h>=14 and ha[h] and ha[h]>0
        if not valid:prev={q:False for q in RULES};continue
        # EMA reclaim: previous close at/below its EMA, current green close above own EMA.
        er=c[i-1]<=e[i-1] and c[i]>e[i] and c[i]>x[1]
        # Range break uses 20 fully completed earlier bars; no future range.
        br=c[i]>max(z[2] for z in b[i-20:i])
        # Session VWAP reclaim: same UTC day; previous value reconstructed separately for scalar audit.
        oldv=oldpv/oldcv if oldcv>0 else None
        vr=oldv is not None and i>0 and b[i-1][0]//86400==d and c[i-1]<=oldv and c[i]>vwap and c[i]>x[1]
        botvol=sum(z[5] for z in b[i-19:i+1])/20
        bot=rs[i] is not None and rs[i]<35 and mac[i]<0 and botvol>0 and x[5]>=1.5*botvol
        if reference:
            # Independent batch expressions for eligibility and reference VWAP.
            prior=[z for z in b[:i] if z[0]//86400==d]
            vv=sum(z[5] for z in prior);vp=sum((z[2]+z[3]+z[4])/3*z[5] for z in prior)
            cur=prior+[x];vv2=sum(z[5] for z in cur);vp2=sum((z[2]+z[3]+z[4])/3*z[5] for z in cur)
            vr=bool(vv>0 and vv2>0 and c[i-1]<=vp/vv and c[i]>vp2/vv2 and c[i]>x[1])
            eligible=[k for k,z in enumerate(context) if z[0]+(60 if m==15 else 240)*60<=at]
            k=eligible[-1] if eligible else -1
            context_ok=k>=50 and ce20[k]>ce50[k] and ce20[k]>ce20[k-1]
        states={'EMA_RECLAIM':context_ok and er,'EMA_RECLAIM_VOL':context_ok and er and volume,'RANGE_BREAK':context_ok and br,'RANGE_BREAK_VOL':context_ok and br and volume,'VWAP_RECLAIM':context_ok and vr,'VWAP_RECLAIM_VOL':context_ok and vr and volume,'BOT_RAW':bot,'BOT_CONTEXT':context_ok and bot,'CONTEXT_EDGE':context_ok,'CONTEXT_DAILY':context_ok}
        details[at]={'atr1h':ha[h],'context':bool(context_ok)}
        for q,ok in states.items():
            # Uniform 6h separation. DAILY control instead samples first eligible bar each UTC day.
            fire=bool(ok and (not prev[q] if q!='CONTEXT_DAILY' else last[q]//86400!=at//86400) and at-last[q]>=21600)
            if fire:out[q].append(at);last[q]=at
            prev[q]=bool(ok)
    return out,details

def outcome(raw,start,entry,a,hours,reference=False):
    # start indexes first minute opening after signal close; entry is that minute open.
    upper=entry+(2 if hours==24 else 4)*a;lower=entry-(1 if hours==24 else 2)*a
    end=start+hours*60
    if end>len(raw):return {'status':'CENSORED','minutes':None}
    if reference:
        ups=[j for j in range(start,end) if raw[j][2]>=upper];downs=[j for j in range(start,end) if raw[j][3]<=lower]
        u=ups[0] if ups else end;d=downs[0] if downs else end
        if d<=u and d<end:return {'status':'FAIL','minutes':d-start}
        if u<end:return {'status':'SUCCESS','minutes':u-start}
        return {'status':'FAIL','minutes':hours*60}
    for j in range(start,end):
        if raw[j][3]<=lower:return {'status':'FAIL','minutes':j-start}
        if raw[j][2]>=upper:return {'status':'SUCCESS','minutes':j-start}
    return {'status':'FAIL','minutes':hours*60}

def wave_events(raw,begin,end):
    """Retrospective local trough labels only. Never used by signals/context."""
    bars=aggregate(raw,60);a=atr(bars);events={24:[],168:[]};last={24:-1,168:-1}
    for i in range(15,len(bars)-3):
        if bars[i][3]>=min(x[3] for x in bars[i-3:i]):continue
        if bars[i][3]>min(x[3] for x in bars[i+1:i+4]):continue
        first=(bars[i][0]-raw[0][0])//60
        j=min(range(first,first+60),key=lambda k:raw[k][3]);at=raw[j][0]
        if not begin<=at<end or not a[i-1] or a[i-1]<=0:continue
        for hours in (24,168):
            if at<=last[hours] or at+60+hours*3600>end:continue
            result=outcome(raw,j+1,raw[j][3],a[i-1],hours)
            assert result==outcome(raw,j+1,raw[j][3],a[i-1],hours,True)
            if result['status']=='SUCCESS':
                hit=at+60+result['minutes']*60
                events[hours].append({'onset':at,'hit':hit,'trough':raw[j][3],'atr1h':a[i-1],'right_confirmation_hours':3})
                last[hours]=hit
    return events

def coverage(rows,events):
    output=[]
    for m in FRAMES:
      for q in RULES:
       for h in (24,168):
        alerts=[r for r in rows if r['frame']==m and r['rule']==q and r['hours']==h and r['status']=='SUCCESS'];used=set();lags=[];matches=[]
        for event_id,e in enumerate(events[h]):
            limit=6 if h==24 else 24
            candidates=[(i,r) for i,r in enumerate(alerts) if i not in used and e['onset']<=r['at']<=min(e['hit'],e['onset']+limit*3600) and r['entry']<=e['trough']+(1 if h==24 else 2)*e['atr1h']]
            if candidates:
                i,r=min(candidates,key=lambda x:x[1]['at']);used.add(i);lags.append((r['at']-e['onset'])/3600);matches.append({'event_id':event_id,'alert_at':r['at']})
        total=len(events[h]);output.append({'frame':m,'rule':q,'hours':h,'events':total,'captured_early':len(matches),'missed':total-len(matches),'coverage':len(matches)/total if total else None,'median_onset_lag_hours':statistics.median(lags) if lags else None,'matches':matches})
    return output

def metrics(rows):
    out=[]
    for m in FRAMES:
      for q in RULES:
       for h in (24,168):
        z=[r for r in rows if r['frame']==m and r['rule']==q and r['hours']==h];v=[r for r in z if r['status']!='CENSORED'];n=len(v);k=sum(r['status']=='SUCCESS' for r in v)
        p=k/n if n else None;ci=None
        if n:
            zz=1.959963984540054**2;den=1+zz/n;mid=(p+zz/(2*n))/den;half=math.sqrt(zz*(p*(1-p)/n+zz/(4*n*n)))/den;ci=[mid-half,mid+half]
        days=len({r['at']//86400 for r in v});out.append(dict(frame=m,rule=q,hours=h,alerts=len(z),censored=len(z)-n,evaluable=n,success=k,precision=p,wilson95_descriptive=ci,days=days,quality_descriptive=bool(n>=100 and p>=.7 and ci[0]>=.6)))
    return out

def fixture():
    raw=[];base=1767225600
    for i in range(45*1440):
        c=100+.001*i+3*math.sin(i/750)+.8*math.sin(i/40);o=100 if not raw else raw[-1][4]
        raw.append([base+60*i,o,max(o,c)+.1,min(o,c)-.1,c,10+(i%180==0)*100])
    return raw,base+20*86400,base+38*86400

def load():
    meta=json.loads((ROOT/'source.json').read_text());p=ROOT/'minutes.csv';assert sha(p)==meta['csv_sha256']
    with p.open() as f:raw=[[int(r[0])]+list(map(float,r[1:])) for r in list(csv.reader(f))[1:]]
    raw=[r for r in raw if r[0]<1785542400] # Never build August candidate masks in July pilot.
    return raw,1782864000,1785542400

def verify_source(root=ROOT):
    for name,digest in json.loads((root/"checksums.json").read_text()).items():
        assert sha(root/name)==digest,("source checksum mismatch",name)

def run(out,synthetic):
    verify_source()
    started=time.monotonic();out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    raw,begin,end=fixture() if synthetic else load()
    assert all(raw[i][0]-raw[i-1][0]==60 for i in range(1,len(raw)))
    assert all(x[3]<=min(x[1],x[4])<=max(x[1],x[4])<=x[2] and x[5]>=0 for x in raw)
    records=[];maskdata={}
    for m in FRAMES:
        masks,details=signals(raw,m);ref,_=signals(raw,m,True);assert masks==ref,('scalar masks differ',m)
        for cut in (2*1440,13*1440,21*1440,len(raw)-1440):
            cut-=cut%240;pre,_=signals(raw[:cut],m);last=raw[cut-1][0]+60
            assert all(pre[q]==[t for t in masks[q] if t<=last] for q in RULES),('prefix',m,cut)
        maskdata[str(m)]=masks
        for q,alerts in masks.items():
            for at in alerts:
                if not begin<=at<end:continue
                j=(at-raw[0][0])//60
                if j>=len(raw):continue
                for h in (24,168):
                    # No labels beyond July/fixture end, even though input includes August.
                    result={'status':'CENSORED','minutes':None} if at+h*3600>end else outcome(raw,j,raw[j][1],details[at]['atr1h'],h)
                    if result['status']!='CENSORED':assert result==outcome(raw,j,raw[j][1],details[at]['atr1h'],h,True)
                    records.append(dict(frame=m,rule=q,hours=h,at=at,entry=raw[j][1],atr1h=details[at]['atr1h'],context=details[at]['context'],**result))
    rows=metrics(records)
    events=wave_events(raw,begin,end); wave_rows=coverage(records,events)
    dump(out/'wave-coverage.json',wave_rows)
    rawobj={'synthetic':synthetic,'window':[begin,end],'masks':maskdata,'alerts':records,'events':events}
    with gzip.GzipFile(filename=str(out/'raw.json.gz'),mode='wb',mtime=0) as f:f.write(json.dumps(rawobj,sort_keys=True).encode())
    dump(out/'results.json',rows)
    # Reopen persisted raw evidence and independently count successes/failures/censoring.
    saved=json.loads(gzip.decompress((out/'raw.json.gz').read_bytes()));assert metrics(saved['alerts'])==rows
    assert coverage(saved['alerts'],{int(k):v for k,v in saved['events'].items()})==wave_rows
    for row in rows:
        z=[a for a in saved['alerts'] if a['frame']==row['frame'] and a['rule']==row['rule'] and a['hours']==row['hours']]
        assert row['alerts']==len(z) and row['success']==len([a for a in z if a['status']=='SUCCESS'])
    dump(out/'audit.json',{'status':'PASS','synthetic':synthetic,'cases':20,'summary_rows':40,'alert_outcome_rows':len(records),'prefix_causality':True,'scalar_masks':True,'independent_minute_barriers':True,'zero_rows_retained':True,'raw_sha256':sha(out/'raw.json.gz'),'results_sha256':sha(out/'results.json'),'compute_and_audit_seconds':time.monotonic()-started,'event_coverage':'retrospective trough labels; separate from precision','onset_latency':'measured against retrospective trough; not real-time availability','adoption':'NOT AUTHORISED'})
    report(out,rows,synthetic)
    return rows

def report(out,rows,synthetic):
    s=['# موجات SOL — تقرير المقارنة المحدودة','', '1. بيانات اصطناعية فقط.' if synthetic else '1. SOL، يوليو2026، دخول15m و1h؛20حالة ونتيجتان منفصلتان24h/168h.','2. المال: لم يُقَس.','3. العينة تنبيهات وليست صفقات.','4. الربحية والتكاليف: لم تُقَس.','5. تحقق أغسطس: لم يُشغّل.','6. المقارنة بالاحتفاظ: خارج المرحلة.','7. Defer؛لا اعتماد من الاكتشاف.','8. التالي: مراجعة Lead،لا تجربة تلقائية.']
    def table(title,headers,data):s.extend(['','## '+title,'|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']);s.extend('|'+'|'.join(str(x) for x in r)+'|' for r in data)
    table('1. الهوية',['البند','القيمة'],[['النطاق','SOL فقط؛يوليو2026؛يونيو تسخين'],['الشبكة','10 قواعد×إطارين'],['المرجع','source.json؛scope.json؛minutes.csv'],['المستقبل','24h/168h،دقائق OHLCV فقط للنتيجة']])
    table('2. المال',['المقياس','القيمة'],[['الربح/الخسارة/تكاليف/خروج','لم يُقَس؛خارج المرحلة']])
    table('3. دقة الإشارات',['دقائق الإطار','القاعدة','أفق ساعة','تنبيهات صالحة','نجاح','دقة'],[[r['frame'],r['rule'],r['hours'],r['evaluable'],r['success'],r['precision']] for r in rows])
    table('4. العينة',['الإطار','القاعدة','الأفق','مستبعدة لقصر المستقبل','أيام مختلفة','Wilson وصفي'],[[r['frame'],r['rule'],r['hours'],r['censored'],r['days'],r['wilson95_descriptive']] for r in rows])
    table('5. الثبات',['القياس','الحالة'],[['جيران الإعدادات','لم يُقَس'],['استقلال التنبيهات','غير مثبت؛فصل6h لا يثبت الاستقلال'],['تأخر بداية الموجة/تغطيتها','wave-coverage.json؛تسمية بأثر رجعي،لا تدخل الإشارة']])
    table('تغطية بداية الموجة',['الإطار','القاعدة','الأفق','أحداث','التقط مبكرًا','فات','وسيط التأخر ساعة'],[[r['frame'],r['rule'],r['hours'],r['events'],r['captured_early'],r['missed'],r['median_onset_lag_hours']] for r in json.loads((out/'wave-coverage.json').read_text())])
    table('6. الفترات والضوابط',['البند','الحالة'],[['يوليو','اكتشاف تاريخي تقويمي'],['أغسطس','لم يُشغّل'],['الضوابط','BOT_RAW،BOT_CONTEXT،CONTEXT_EDGE،CONTEXT_DAILY'],['اختيار مرشح','لا اختيار آلي؛مراجعة Lead أولًا']])
    table('7. الجودة',['الإطار','القاعدة','الأفق','NS100/P70/Wilsonlow60 وصفي','اعتماد'],[[r['frame'],r['rule'],r['hours'],r['quality_descriptive'],'غير مأذون'] for r in rows])
    table('قاموس القواعد',['المعرف','المعنى'],[['EMA_RECLAIM','استرداد المتوسط20 داخل سياق صاعد'],['RANGE_BREAK','اختراق أعلى20شمعة سابقة'],['VWAP_RECLAIM','استرداد متوسط السعر المرجح بالحجم اليوميUTC'],['VOL','حجم≥1.5متوسط20سابقة'],['BOT_RAW','ضابط شروط البوت الأساسية،ليس تشغيل البوت'],['BOT_CONTEXT','ضابط البوت مع سياق الصعود'],['CONTEXT_EDGE/DAILY','ضابط بدء السياق/أول ساعة مؤهلة يوميًا']])
    s+=['','إعادة التشغيل: python waves.py --synthetic --out fixture أو python waves.py --out market.','الحاجز المعاكس أولًا عند لمس الاثنين في الدقيقة نفسها. لا يُضم أفقا اليوم والأسبوع في دقة واحدة. Wilson وصفي بسبب الاعتماد والتجريب المتعدد؛لا احتمال نجاح مضمون. البيانات المستقبلية للتقييم فقط؛سياق الصعود يستخدم آخر شمعة مكتملة. لا ادعاء اكتشاف أفضل مؤشر في التداول كله.']
    (out/'REPORT.md').write_text('\n'.join(s)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--synthetic',action='store_true');p.add_argument('--out',default='run');a=p.parse_args();run(a.out,a.synthetic)
