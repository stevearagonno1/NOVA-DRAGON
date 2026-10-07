"""L0094 fixed all-pairs stage. Reuses L0085 partition writer and scalar audit."""
from pathlib import Path
import argparse,collections,gzip,hashlib,heapq,itertools,json,math,statistics,time
import research85 as R
ROOT=Path(__file__).resolve().parent
ASSETS=['BTCUSDT','ETHUSDT','SOLUSDT'];MODES=['AND0','AND2','OR0']
BRANCH='agent/l0094-all-pairs-2026-10-07'
DEST='history/research/hyp_lab_out/L0094-all-pairs'
write=R.write_json
def configure(raw):
    names=[a+'_P'+str(p) for a in ASSETS for p in range(3)]
    R.ASSETS=names;R.HEADER=['candidate','a','b','mode']+[s+'_'+n for s in names for n in ['signals','matched','lag_sum']]
    return R.inflate(raw)
def frozen(synthetic=False):
    parent=json.loads(gzip.decompress((ROOT/'parent93.json.gz').read_bytes()))
    assert not parent['synthetic'] and len(parent['grid'])==482
    if synthetic:
        # Six rules, nine short artificial panels through the very same writer/audit/report.
        grid=parent['grid'][:6];assets={}
        for ai,asset in enumerate(ASSETS):
            for pi in range(3):
                mm=[hex(sum(1<<b for b in range(10,170) if (b+j*3+ai+pi)%(7+j)==0)) for j in range(6)]
                ev=[{'onset':x,'window':list(range(x-2,x+3)),'mask':sum(1<<b for b in range(x-2,x+3))} for x in [30,70,110,150]]
                assets[asset+'_P'+str(pi)]={'valid':hex(sum(1<<b for b in range(10,171))),'masks':mm,'events':ev}
        return {'synthetic':True,'grid':grid,'assets':assets,'budget':51,'source_parent_sha256':R.sha(ROOT/'parent93.json.gz')}
    assets={}
    for asset in ASSETS:
        a=parent['assets'][asset];mm=[a['masks'][q['id']] for q in parent['grid']]
        for pi,p in enumerate(a['periods']):
            assets[asset+'_P'+str(pi)]={'valid':hex(sum(1<<b for b in p['valid'])),'masks':mm,
              'events':[{**e,'mask':sum(1<<b for b in e['window'])} for e in p['events']]}
    return {'synthetic':False,'grid':parent['grid'],'assets':assets,'budget':348245,'source_parent_sha256':R.sha(ROOT/'parent93.json.gz')}
def pooled(row,asset,raw):
    per=[R.metric(row[asset+'_P'+str(p)+'_signals'],row[asset+'_P'+str(p)+'_matched'],len(raw['assets'][asset+'_P'+str(p)]['events'])) for p in range(3)]
    ns=sum(z['signals'] for z in per);tp=sum(z['matched_events'] for z in per);ne=sum(z['events'] for z in per)
    return dict(asset=asset,candidate=row['candidate'],a=row['a'],b=row['b'],mode=row['mode'],**R.metric(ns,tp,ne),periods=per,
                eligible=ns>=20 and tp/ne>=.3 and all(z['signals']>=3 and z['recall']>=.15 for z in per),
                minimum_period_precision=min(z['precision'] for z in per))
def summary(out,raw):
    heaps={a:[] for a in ASSETS};parents={};eligible_counts=collections.Counter();zero=0;total=0
    for row in R.read_rows(out):
        total+=1
        for asset in ASSETS:
            d=pooled(row,asset,raw)
            if row['mode']=='S':parents[asset,row['candidate']]=d
            if not d['signals']:zero+=1
            if d['eligible'] and row['mode']!='S':
                eligible_counts[asset]+=1;key=(d['minimum_period_precision'],d['precision'],d['recall'],-d['candidate'])
                item=(key,d['candidate'],d);h=heaps[asset]
                if len(h)<20:heapq.heappush(h,item)
                elif item[:2]>h[0][:2]:heapq.heapreplace(h,item)
    top={a:[item[2] for item in sorted(h,reverse=True)] for a,h in heaps.items()}
    details=[];data=configure(raw)
    for asset in ASSETS:
        for d in top[asset]:
            added=[];lost=[];lags=[];comparison=[]
            pairsets=[];parentssets={d['a']:[],d['b']:[]}
            for pi in range(3):
                valid,mm,events=data[ASSETS.index(asset)*3+pi]
                x=R.combine(mm[d['a']],mm[d['b']],d['mode'],valid)
                got={e['onset'] for e in events if x&e['mask']};pairsets.append(got)
                for e in events:
                    common=x&e['mask']
                    if common:lags.append((common&-common).bit_length()-1-e['onset'])
                for k in parentssets:
                    v=R.combine(mm[k],0,'S',valid);parentssets[k].append({e['onset'] for e in events if v&e['mask']})
            for k,ss in parentssets.items():
                p=parents[asset,k];comparison.append(dict(parent=k,precision=p['precision'],recall=p['recall'],added=sum(len(x-y) for x,y in zip(pairsets,ss)),lost=sum(len(y-x) for x,y in zip(pairsets,ss))))
            ns=d['signals'];tp=d['matched_events'];z=1.959963984540054;den=1+z*z/ns;ph=tp/ns;center=(ph+z*z/(2*ns))/den;half=z*math.sqrt(ph*(1-ph)/ns+z*z/(4*ns*ns))/den
            d.update(rule=[raw['grid'][d['a']],raw['grid'][d['b']]],parent_comparison=comparison,wilson95=[center-half,center+half],median_lag=statistics.median(lags) if lags else None,
                     quality_pass=d['precision']>=.7 and d['recall']>=.3 and ns>=20 and center-half>=.6 and statistics.median(lags)<=1,
                     marginal_gain=all(d['precision']>=p['precision']+.05 and d['recall']>=.8*p['recall'] for p in comparison))
            details.append(d)
    selection={'top20_eligible_pairs_by_asset':top,'ranking':'minimum_period_precision,pooled_precision,recall,candidate_id','validation_read':False,'adoption':'NOT AUTHORISED'}
    R.write_json(out/'selection.json',selection);R.write_json(out/'parent_comparison.json',details)
    R.write_json(out/'analysis.json',dict(state='DISCOVERY_ONLY',adoption='NOT AUTHORISED',quality_and_marginal_passes=[{'asset':d['asset'],'candidate':d['candidate']} for d in details if d['quality_pass'] and d['marginal_gain']],eligible_pair_counts=dict(eligible_counts),all_rows=total,zero_signal_asset_rows=zero,limits='Only frozen top20 per asset get detailed quality checks;no claim of exhaustive quality evaluation of every pair. Raw counts for all pairs retained.'))
    lines=['# L0094 — مسح أزواج الإشارات','', '1.482منفردًا وكل115921زوجًا بثلاث طرق؛BTC/ETH/SOL،4h،ثلاثفترات2025.' if not raw['synthetic'] else '1.فحص اصطناعي فقط؛لاقياسسوق.',
           '2.المال:not measured.','3.348245حالة و3134205تقييممقطع فيالسوق؛لاصفقات.','4.الربحيةوالتكاليف:not measured.','5.فترةعمياء:not measured.','6.الاحتفاظ:not measured.','7.Defer adoption؛اكتشاففقط.','8.التالي:مراجعةالقائد،لاثلاثياتتلقائية.']
    def table(title,heads,rows):
        lines.extend(['','## '+title,'|'+'|'.join(heads)+'|','|'+'|'.join(['---']*len(heads))+'|']);lines.extend('|'+'|'.join(map(str,r))+'|' for r in rows)
    table('1.الهوية',['البند','القيمة'],[['المصدر','parent93.json.gz وبصمةscope/source'],['الطرق','AND0/AND2/OR0؛نبضاتL0093المجمدة'],['البيانات','تطويرتاريخيمكشوف؛نافذةنجاح±2 ثابتة']])
    table('2.المال',['المقياس','الحالة'],[['الصفقات/الربحية/التكاليف/الخروج','not measured — outside this phase']])
    table('3.أعلى20مؤهلًالكلعملة',['العملة','ID','الطريقة','تنبيهات','ملتقط/أحداث','الدقة','الاسترجاع'],[[d['asset'],d['candidate'],d['mode'],d['signals'],str(d['matched_events'])+'/'+str(d['events']),f"{d['precision']:.2%}",f"{d['recall']:.2%}"] for d in details])
    table('4.العينةوالتوقيت',['العملة','ID','Wilson95وصفي','وسيطالتأخير'],[[d['asset'],d['candidate'],d['wilson95'],d['median_lag']] for d in details])
    table('5.الثبات',['العملة','ID','المقطع','تنبيهات','الدقة','الاسترجاع'],[[d['asset'],d['candidate'],i+1,z['signals'],f"{z['precision']:.2%}",f"{z['recall']:.2%}"] for d in details for i,z in enumerate(d['periods'])])
    table('6.المكونانالمنفردان',['العملة','ID','المكون','فرق الدقة','فرق الاسترجاع','أحداثمضافة','أحداثمفقودة'],[[d['asset'],d['candidate'],raw['grid'][p['parent']]['id'],f"{d['precision']-p['precision']:.2%}",f"{d['recall']-p['recall']:.2%}",p['added'],p['lost']] for d in details for p in d['parent_comparison']])
    table('7.الشروط',['المعيار','المطلوب','الحالة'],[['الأهلية','NS20/R30%؛كلربعNS3/R15%','مطبقةقبلالترتيب'],['الجودة','P70%/R30%/Wilsonlow60%/lag≤1','راجعparent_comparison.json لكلالمرشحينالمجمدين'],['الإضافةللمكونين','دقة+5نقاطواحتفاظ80%منRلكلمكون','وصفي؛مطبّقعلىأفضل20المسجلة'],['الاعتماد','تحققمنفصل','not measured؛NOT AUTHORISED']])
    lines+=['','كلالحالاتبمافيهاالصفرمحفوظةفيscores-*.csv.gz؛الأقنعةوالأحداثبـraw_signals.json.gz. p-values/ضوابطنقلدورية/تصحيحتعددالبحث:not measured؛لاادعاءتفوقمصحح. Wilsonيفترضاستقلالالتنبيهاتولايدعمحكمًاخارجالعينة. أعلى20هيترتيبمثبتقبلالقياسولاعودةلاختياربديلمنتحقق.',
            'إعادةالحساب:python run94.py --mode measure --out market؛للاصطناعي--mode fixture. كلالمصادرتثبتبـsource.json.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
def execute(out,synthetic=False,stop_after=None):
    started=time.monotonic()
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    source=json.loads((ROOT/'source.json').read_text())
    for name,digest in source['sha256'].items():assert R.sha(ROOT/name)==digest,name
    raw=frozen(synthetic);data=configure(raw);keys=list(R.candidates(raw['grid']));assert len(keys)==raw['budget']
    encoded=gzip.compress(json.dumps(raw,sort_keys=True).encode(),mtime=0);saved=out/'raw_signals.json.gz'
    if saved.exists():assert saved.read_bytes()==encoded
    else:R.atomic(saved,encoded)
    manifest={'raw_sha256':R.sha(saved),'budget':len(keys),'synthetic':synthetic,'parts':[],'source_sha256':R.sha(ROOT/'source.json')}
    old=json.loads((out/'checkpoint.json').read_text()) if (out/'checkpoint.json').exists() else None
    if old:assert all(old[k]==manifest[k] for k in ['raw_sha256','budget','synthetic','source_sha256'])
    batch=20 if synthetic else 10000
    for offset in range(0,len(keys),batch):
        name='scores-%05d.csv.gz'%(offset//batch);path=out/name
        rec=next((r for r in old['parts'] if r['file']==name),None) if old else None
        if rec:
            assert path.exists() and R.sha(path)==rec['sha256'] and rec['first']==offset
        else:
            rows=[R.row_for(k,data) for k in keys[offset:offset+batch]];b=R.batch_bytes(rows)
            if path.exists():assert path.read_bytes()==b,'orphan partition differs'
            else:R.atomic(path,b)
            rec={'file':name,'first':offset,'rows':len(rows),'bytes':len(b),'sha256':R.sha(path)}
        manifest['parts'].append(rec);R.write_json(out/'checkpoint.json',manifest)
        print('SCORED',offset+rec['rows'],'/',len(keys),flush=True)
        if stop_after is not None and len(manifest['parts'])>=stop_after:return
    begin=time.monotonic();R.audit(out);a=json.loads((out/'audit.json').read_text());a['audit_seconds']=time.monotonic()-begin;a['compute_seconds']=time.monotonic()-started;R.write_json(out/'audit.json',a);summary(out,raw)
def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['fixture','measure'],required=True);p.add_argument('--out',required=True);p.add_argument('--stop-after',type=int);a=p.parse_args();execute(a.out,a.mode=='fixture',a.stop_after)
if __name__=='__main__':main()
