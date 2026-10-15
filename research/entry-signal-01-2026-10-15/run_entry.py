"""Discovery only: immutable fixed-feature alerts; no time/return success barrier."""
from array import array
import argparse,csv,datetime as dt,gzip,hashlib,io,json,math,os,struct,sys,time,urllib.request,zipfile
from decimal import Decimal
from pathlib import Path
from entry_core import RULES,triggers,outcomes,describe,empty,add,self_test
from delivery import API,publish,REPO

P=Path(__file__).resolve().parent
R=struct.Struct('<q14d')
def get(url):
    with urllib.request.urlopen(url,timeout=45) as f:return f.read()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def stamp(s):return int(dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc).timestamp()*1000)
def size():return sum(f.stat().st_size for f in P.rglob('*') if f.is_file())
def check_budget():assert size()<=125000000,'Task storage exceeds125MB'

def real_source(spec):
    source=spec['data'];base='https://raw.githubusercontent.com/'+REPO+'/'+source['feature_commit']+'/'+source['feature_path']
    raw=get(base+'FEATURES.json');assert blob(raw)==source['manifest_git_sha']
    manifest=json.loads(raw);start=stamp(spec['start']);end=stamp(spec['end_exclusive'])
    prices=array('q');first=None;expected=stamp(source['collection_start'])
    for month,digest in source['raw_sha256'].items():
        if month>=spec['end_exclusive'][:7]:continue
        url='https://raw.githubusercontent.com/'+REPO+'/'+source['raw_commit']+'/'+source['raw_path']+'BTCUSDT-1m-'+month+'.zip'
        content=get(url);assert hashlib.sha256(content).hexdigest()==digest
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            assert len(z.namelist())==1
            with z.open(z.namelist()[0]) as f:
                for row in csv.reader(io.TextIOWrapper(f)):
                    t=int(row[0])//1000;assert t==expected;expected+=60000
                    if first is None:first=t
                    q=Decimal(row[4])*100000000;assert q==q.to_integral_value()
                    prices.append(int(q))
        check_budget()
    assert expected==end and first is not None
    def chunks():
        for d in manifest['files']:
            if d['first_open_ms']>=end:continue
            b=get(base+d['file']);assert hashlib.sha256(b).hexdigest()==d['sha256']
            assert len(b)==d['records']*120
            for i,row in enumerate(R.iter_unpack(b)):
                assert row[0]==d['first_open_ms']+i*d['frame_minutes']*60000
            yield d['frame_minutes'],b
    return first,prices,chunks(),{'manifest_git_sha':blob(raw),'feature_commit':source['feature_commit'],'raw_end_exclusive':spec['end_exclusive']}

def fixture(spec):
    first=stamp('2025-09-30');n=1440*3;prices=array('q',(10000000000+(i%17-8)*1000000 for i in range(n)))
    chunks=[]
    for frame in (1,5,15,60):
        b=bytearray()
        for i,t in enumerate(range(first,first+n*60000,frame*60000)):
            v=[0.0]*14
            for _,_,k,level,_ in RULES:v[k]=level+(-2 if i%3==0 else 2)
            b.extend(R.pack(t,*v))
        chunks.append((frame,bytes(b)))
    return first,prices,iter(chunks),{'fixture':True,'description':'three-day deterministic price and feature sequence; no market result'}

def analyse(spec,mode):
    out=P/mode;out.mkdir(exist_ok=True)
    old=list(out.glob('events-*.csv.gz'))
    assert not old,'Existing event evidence present; do not overwrite or start a duplicate. Ask Lead to inspect.'
    first,prices,chunks,identity=(fixture(spec) if mode=='rehearsal' else real_source(spec))
    begin=stamp('2025-10-01') if mode=='rehearsal' else stamp(spec['start'])
    end=stamp('2025-10-03') if mode=='rehearsal' else stamp(spec['end_exclusive'])
    labels=outcomes(prices);stats={};previous={};writers={};handles={};counts={f:0 for f in (1,5,15,60)}
    fields=['rule','kind','frame_minutes','feature_open_ms','signal_available_ms','reference_close_ms','reference_close_1e8','prior_direction','next_direction','next_change_close_ms','first_above_close_ms','wait_minutes','observed_minutes']
    def update(rule,kind,frame,month,d):
        for period in (month,'ALL_DISCOVERY'):
            key=(rule,kind,frame,period)
            if key not in stats:stats[key]=empty()
            add(stats[key],d)
    records=0;event_count=0;feature_digest=hashlib.sha256()
    try:
        for frame,b in chunks:
            feature_digest.update(str(frame).encode()+b)
            for row in R.iter_unpack(b):
                opened=row[0];available=opened+frame*60000;values=row[1:]
                assert all(math.isfinite(x) for x in values)
                old=previous.get(frame);previous[frame]=(opened,values)
                if old is not None:assert opened-old[0]==frame*60000
                if not begin<=available<end:continue
                assert old is not None,'Insufficient previous closed bar'
                index=(available-first)//60000-1
                assert first+index*60000+60000==available and 0<=index<len(prices)
                d=describe(prices,labels,index);month=dt.datetime.fromtimestamp(available/1000,dt.timezone.utc).strftime('%Y-%m')
                update('BASELINE','baseline',frame,month,d);counts[frame]+=1
                for rule,kind in triggers(old[1],values):
                    key=(frame,opened,rule);records+=1
                    update(rule,kind,frame,month,d);event_count+=1
                    if month not in writers:
                        h=gzip.open(out/('events-'+month+'.csv.gz'),'wt',newline='');handles[month]=h;w=csv.writer(h);writers[month]=w;w.writerow(fields)
                    def close_time(i):return '' if i<0 else first+(i+1)*60000
                    writers[month].writerow([rule,kind,frame,opened,available,available,int(prices[index]),d['prior_direction'],d['next_direction'],close_time(d['next_change_index']),close_time(d['first_above_index']),'' if d['wait_minutes'] is None else d['wait_minutes'],d['observed_minutes']])
            check_budget()
    finally:
        for h in handles.values():h.close()
    # Every registered zero-signal group is retained, including each month.
    months=sorted({k[3] for k in stats if k[3]!='ALL_DISCOVERY'})
    for frame in counts:
        for rule,kind,*_ in RULES:
            for month in months+['ALL_DISCOVERY']:stats.setdefault((rule,kind,frame,month),empty())
    summary=[]
    for (rule,kind,frame,period),s in sorted(stats.items()):
        assert s['next_up']+s['next_down']+s['next_unobserved']==s['n']
        assert s['above_seen']+s['above_not_seen']==s['n']
        baseline=stats[('BASELINE','baseline',frame,period)]
        observed=s['next_up']+s['next_down'];base_observed=baseline['next_up']+baseline['next_down']
        rate=s['next_up']/observed if observed else None;br=baseline['next_up']/base_observed if base_observed else None
        summary.append(dict(rule=rule,kind=kind,frame_minutes=frame,period=period,**s,next_up_fraction=rate,baseline_next_up_fraction=br,lift=None if rate is None or br is None else rate-br,mean_wait=None if not s['above_seen'] else s['wait_sum']/s['above_seen']))
    expected={f:(end-begin)//(f*60000) for f in counts};assert counts==expected,(counts,expected)
    assert sum(s['n'] for (r,k,f,p),s in stats.items() if r!='BASELINE' and p=='ALL_DISCOVERY')==event_count
    csv_rows=0;identities=set()
    for filename in sorted(out.glob('events-*.csv.gz')):
        with gzip.open(filename,'rt',newline='') as evidence:
            for r in csv.DictReader(evidence):
                ident=(r['rule'],r['frame_minutes'],r['feature_open_ms']);assert ident not in identities;identities.add(ident)
                assert int(r['signal_available_ms'])==int(r['feature_open_ms'])+int(r['frame_minutes'])*60000
                for k in ['next_change_close_ms','first_above_close_ms']:
                    if r[k]:assert int(r[k])>int(r['signal_available_ms'])
                csv_rows+=1
    assert csv_rows==event_count
    tests=self_test();(out/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
    audit={'status':'PASS_INTEGRITY','self_test':tests,'eligible_bars':counts,'expected_eligible_bars':expected,'event_rows':event_count,'summary_reconciled':True,'unique_event_identity':'rule+frame+feature_open; one evaluation per bar; overlapping alerts are NOT independent trials','future_outcomes_not_signal_inputs':True,'feature_stream_sha256':feature_digest.hexdigest()}
    (out/'AUDIT.json').write_text(json.dumps(audit,indent=2)+'\n')
    result={'status':'PASS_REHEARSAL_ONLY' if mode=='rehearsal' else 'DESCRIPTIVE_DISCOVERY_LEAD_REVIEW_PENDING','mode':mode,'data_identity':identity,'registered_series':40,'rule_families':10,'directional_rule_series':32,'activity_only_series':8,'event_rows':event_count,'summary_groups':len(summary),'eligible_bars':counts,'start_ms':begin,'end_exclusive_ms':end,'selection_or_validation':False,'future_horizon':'no fixed time barrier; follow-up ends at the registered discovery-data boundary','outcome_warning':'An eventual higher close alone does not establish a good entry; next-change direction, prior direction, waiting time and censoring must be read together. No high-rate acceptance gate.','financial':'not measured — outside this phase','confidence_or_significance':'not measured; overlapping descriptive alerts are not independent binomial trials','workspace_bytes':size()}
    (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    report='# دراسة إشارات الدخول المنفردة\n\n'
    report+='الحالة: '+result['status']+'\n\n'
    report+='1. جربنا شروط دخول مستقلة بالإعدادات القائمة على BTCUSDT وأربعة أطر.\n2. الربح: غير مقاس — خارج المرحلة.\n3. عدد الإشارات: '+str(event_count)+'؛ ليست صفقات مستقلة.\n4. معامل الربح: غير مقاس — خارج المرحلة.\n5. الفترة المستقلة: لم تختبر؛ هذه جولة اكتشاف وصفية.\n6. المقارنة: الأوقات المؤهلة في الإطار والشهر نفسيهما.\n7. الحكم: بانتظار مراجعة القائد؛ لا اختيار فائز أو اعتماد تداول.\n8. التالي: مراجعة التوقيت والأخطاء قبل أي دمج.\n\n'
    report+='## 1. هوية التجربة\n| البند | القيمة |\n|---|---|\n| الأصل | BTCUSDT Spot |\n| البداية | '+str(begin)+' مللي ثانية UTC |\n| النهاية الحصرية | '+str(end)+' مللي ثانية UTC |\n| الأطر | 1 و5 و15 و60 دقيقة |\n| عدد السلاسل | 32 اتجاهية و8 نشاط فقط |\n\n'
    for title in ['2. إحصاءات المال','3. إحصاءات الصفقات','4. المخاطر والتراجع']:
        report+='## '+title+'\n| البند | القيمة |\n|---|---|\n| القياسات المالية والصفقات | غير مقاسة — خارج المرحلة |\n\n'
    report+='## 5. الإعدادات والاستقرار\n| البند | القيمة |\n|---|---|\n| إعدادات المؤشرات | ثابتة؛ لا مسح إعدادات |\n| المحاولات الصفرية | محفوظة في SUMMARY.json |\n| الاستقرار الوصفي | تفصيل شهري؛ لا ادعاء دلالة إحصائية |\n\n'
    report+='## 6. الفترات والمقارنة\n| البند | القيمة |\n|---|---|\n| الفترة الحالية | الاكتشاف فقط |\n| التحقق والاحتياط | لم تحسب نتائجهما |\n| خط المقارنة | BASELINE في SUMMARY.json لكل إطار وشهر |\n| الاحتفاظ بالعملة | غير مقاس — خارج المرحلة |\n\n'
    report+='## 7. شروط اعتماد التداول\n| البند | القيمة |\n|---|---|\n| اعتماد تداول | غير مطروح في هذه الجولة |\n| عتبة نجاح مؤشر | لا توجد عتبة مرتفعة مفروضة |\n| قبول التسليم | سلامة الفحوص والتعداد وحفظ كل الأدلة |\n\n'
    report+='## المثبت والحدود\nالفحص الحسابي لا يثبت أفضلية إشارة. الإشارات المتزامنة والمتداخلة ليست تجارب مستقلة. ظهور إغلاق أعلى لاحقًا قد يأتي بعد هبوط وانتظار طويل؛ تقرأ معه جهة أول تغير ومدة الانتظار والتغطية المتاحة. عدم ظهور ارتفاع قبل نهاية البيانات لا يثبت أنه لن يحدث مستقبلًا. ATR والحجم نشاط فقط. لا أهداف حركة أو مهلة نجاح مفروضة أو مخارج أو أرباح.\n\n'
    report+='## المصطلحات\n| الحقل | المعنى |\n|---|---|\n| next_up | أول إغلاق مختلف لاحقًا أعلى من إغلاق الإشارة |\n| above_seen | ظهر إغلاق أعلى قبل نهاية بيانات الاكتشاف |\n| above_not_seen | لم يظهر ضمن المتابعة المتاحة؛ لا حكم أبدي |\n| wait_minutes | الزمن المرصود حتى أول إغلاق أعلى؛ دون حد نجاح |\n| lift | فرق وصفي عن الأوقات المؤهلة؛ ليس دلالة إحصائية |\n| prior_direction | جهة آخر تغير إغلاق معلوم قبل الإشارة أو عندها |\n\n'
    report+='## الأسماء المستخدمة\n| التعبير | المعنى |\n|---|---|\n| السلسلة المستقلة | شرط واحد وإطار واحد |\n| مجموعة النشاط | قياس ATR أو الحجم دون افتراض اتجاه |\n| نتيجة وصفية | أعداد مرصودة دون اختيار فائز أو تعميم |\n\n'
    report+='الأمر: python3 run_entry.py '+('--rehearsal ' if mode=='rehearsal' else '')+'--publish --source-commit COMMIT_FROM_PAPER\n'
    (out/'REPORT.md').write_text(report)
    for f in out.iterdir():assert f.stat().st_size<25000000
    check_budget();return out,result

def main(args):
    started=time.time();spec=json.loads((P/'protocol.json').read_text())
    assert args.rehearsal or args.publish,'Production must deliver verified work-branch evidence'
    api=API(os.environ.get('GH_TOKEN','')) if args.publish else None
    if api:
        r=api.call('GET','/repos/'+REPO);assert r.get('permissions',{}).get('push') is True
    mode='rehearsal' if args.rehearsal else 'execution';out,result=analyse(spec,mode)
    if api:
        branch=spec['readiness_branch'] if args.rehearsal else spec['execution_branch']
        dest=spec['repository_path']+mode+'/'
        files={dest+f.name:f for f in out.iterdir() if f.is_file() and f.name!='DELIVERY.json'}
        delivered=publish(api,branch,args.source_commit,files)
        receipt={'status':'PASS_REHEARSAL_ONLY' if args.rehearsal else 'ENTRY_DISCOVERY_DELIVERED_LEAD_REVIEW_PENDING','source_commit':args.source_commit,'data_delivery':delivered,'elapsed_before_receipt_upload_seconds':time.time()-started,'result':result}
        (out/'DELIVERY.json').write_text(json.dumps(receipt,indent=2)+'\n')
        receipt['receipt_delivery']=publish(api,branch,delivered['commit'],{dest+'DELIVERY.json':out/'DELIVERY.json'})
        receipt['local_elapsed_through_verified_receipt_seconds']=time.time()-started
        (out/'LOCAL-RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('تم' if args.publish else 'PASS_LOCAL_REHEARSAL')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--rehearsal',action='store_true');p.add_argument('--publish',action='store_true');p.add_argument('--source-commit',required=True);args=p.parse_args()
    try:
        assert len(args.source_commit)==40 and all(c in '0123456789abcdef' for c in args.source_commit)
        main(args)
    except Exception as exc:
        token=os.environ.get('GH_TOKEN','');reason=str(exc)
        if token:reason=reason.replace(token,'[REDACTED]')
        (P/'ERROR.json').write_text(json.dumps({'type':type(exc).__name__,'reason':reason,'action':'calculate/audit/publish entry discovery'},ensure_ascii=False,indent=2)+'\n')
        print('فشل: '+(reason.replace('\n',' ') or type(exc).__name__)[:400]);sys.exit(1)
