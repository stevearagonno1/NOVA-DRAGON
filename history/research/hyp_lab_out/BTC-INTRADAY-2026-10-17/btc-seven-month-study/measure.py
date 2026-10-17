from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,gzip,importlib.util,time,datetime
P=Path(__file__).parent;WORK=P.parent
NAMES={'trend':'وجود اتجاه صاعد','breakout':'اختراق قمة آخر ثلاث ساعات','rebound':'ضعف أو تشبع بيعي سابق','other':'دون الأوصاف الثلاثة'}
def dump(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False))
def csvzip(df,path,index=False):
 payload=df.to_csv(index=index,float_format='%.17g').encode();path.write_bytes(gzip.compress(payload,mtime=0));return hashlib.sha256(path.read_bytes()).hexdigest()
def load_method():
 spec=importlib.util.spec_from_file_location('month_method',P/'analyze_month.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def run():
 started=time.monotonic();reg=json.loads((P/'registration.json').read_text());assert hashlib.sha256((P/'analyze_month.py').read_bytes()).hexdigest()==reg['analyzer_sha256'];M=load_method();src=WORK/'btc-month-study/BTCUSDT_1m.parquet';expected=json.loads((WORK/'btc-month-study/source_manifest.json').read_text())['source_sha256'];allrows=[];audits=[]
 if src.exists():
  actual=hashlib.sha256(src.read_bytes()).hexdigest();assert actual==expected;rawall=pd.read_parquet(src,engine='fastparquet');tt=rawall.open_time.to_numpy(np.int64);tt=np.where(tt>1e14,tt//1000,tt);rawall.index=pd.to_datetime(tt,unit='ms',utc=True)
  # Only this task's disposable local download is removed; repository and retained evidence stay intact.
  src.unlink();print('SOURCE_LOADED_AND_DISPOSABLE_DOWNLOAD_REMOVED',flush=True)
 else:rawall=None
 for month in reg['all_compared_months']:
  out=P/month;out.mkdir(exist_ok=True);start=pd.Timestamp(month+'-01',tz='Asia/Aden');end=start+pd.offsets.MonthBegin();days=(end.date()-start.date()).days
  if month in ['2024-01','2025-12']:
   folder=WORK/('btc-month-study' if month=='2024-01' else 'btc-month-comparison');old=json.loads((folder/'summary.json').read_text());ev=pd.read_csv(folder/'events.csv');daily=pd.read_csv(folder/'daily_counts.csv');counts={k:int(ev[k].sum()) for k in ['trend','breakout','rebound']};counts['other']=int((~ev[['trend','breakout','rebound']].any(axis=1)).sum());assert len(ev)==old['events']==daily.total.sum();assert {k:counts[k] for k in ['trend','breakout','rebound']}==old['overlapping_flag_counts'];ss=old['sensitivity'];audit={'month':month,'source':'prior saved event rows recounted','events':len(ev),'summary_counts_reconciled':True};origin=str(folder.name)
  else:
   if rawall is not None:
    raw=rawall.loc[(rawall.index>=start.tz_convert('UTC')-pd.Timedelta(days=4))&(rawall.index<end.tz_convert('UTC'))].copy();raw.index.name='time_utc';csvzip(raw,out/'source_minutes.csv.gz',True)
   else:
    raw=pd.read_csv(out/'source_minutes.csv.gz',index_col='time_utc');raw.index=pd.to_datetime(raw.index,utc=True)
   assert len(raw)==(days+4)*1440;assert not raw.index.duplicated().any();assert (np.diff(raw.index.asi8)==60*10**9).all();assert np.isfinite(raw[['open','high','low','close','volume']]).all().all();assert ((raw.low>0)&(raw.volume>=0)&(raw.low<=raw[['open','close']].min(axis=1))&(raw.high>=raw[['open','close']].max(axis=1))).all()
   b=raw.resample('15min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),volume=('volume','sum'),minutes=('close','count'));b.index+=pd.Timedelta(minutes=15)-pd.Timedelta(milliseconds=1);assert b.minutes.eq(15).all();x=M.features(b);times,condition,crossings=M.accepted(x,.5,month);rows=[]
   for no,t in enumerate(times):
    z=x.loc[t];kind=next((k for k in ['rebound','breakout','trend'] if bool(z[k])),'other');local=t.tz_convert('Asia/Aden');rows.append({'event':no+1,'time_aden':local.isoformat(),'time_utc':t.isoformat(),'day':str(local.date()),'category':kind,**{k:float(z[k]) for k in ['close','price60_before','return60_pct','prior_return60_pct','rsi14','prior_rsi_min','ema20','ema50','prior_high3h','volume60','volume_previous60','volume_ratio']},**{k:bool(z[k]) for k in ['trend','breakout','rebound']}})
   ev=pd.DataFrame(rows);ev.to_csv(out/'events.csv',index=False,float_format='%.12g');csvzip(x,out/'bars15m.csv.gz',True);all_days=pd.DataFrame({'day':pd.date_range(start,end,inclusive='left').strftime('%Y-%m-%d')});daily=ev.groupby(['day','category']).size().unstack(fill_value=0).reindex(columns=['rebound','breakout','trend','other'],fill_value=0).reset_index();daily=all_days.merge(daily,on='day',how='left').fillna(0);daily['total']=daily[['rebound','breakout','trend','other']].sum(axis=1).astype(int);daily.to_csv(out/'daily_counts.csv',index=False)
   ss=[];scalar_checks=0
   for threshold in [.25,.5,1.0]:
    accepted,nn,pp=M.accepted(x,threshold,month)
    # Reconstruct rises, day restriction, pulse and spacing without the vector routine.
    found=[];prev=False;last=None
    for i in range(len(b)):
     t=b.index[i];local=t.tz_convert('Asia/Aden');ok=i>=60 and local.strftime('%Y-%m')==month and local.date()==b.index[i-4].tz_convert('Asia/Aden').date() and (b['minutes'].iloc[i-60:i+1]==15).all() and np.isfinite(x.ema50.iloc[i]) and np.isfinite(x.rsi14.iloc[i]);above=bool(ok and (b.close.iloc[i]/b.close.iloc[i-4]-1)*100>=threshold)
     if above and not prev and (last is None or (t-last).total_seconds()>=3600):found.append(t);last=t
     prev=above
    assert accepted==found;scalar_checks+=len(accepted);ss.append({'threshold_pct':threshold,'events':len(accepted),'days':len(set(t.tz_convert('Asia/Aden').date() for t in accepted)),'condition_bars':nn,'crossings':pp})
   for day in [7,15,23]:
    cutoff=pd.Timestamp(f'{month}-{day:02d} 23:59:59.999',tz='Asia/Aden').tz_convert('UTC');partial=M.features(b.loc[b.index<=cutoff]);aa,_,_=M.accepted(partial,.5,month);assert aa==[t for t in times if t<=cutoff];assert np.allclose(partial[['rsi14','ema20','ema50','volume_ratio']],x.loc[partial.index,['rsi14','ema20','ema50','volume_ratio']],equal_nan=True)
   for z in rows:
    t=pd.Timestamp(z['time_utc']);past=t-pd.Timedelta(hours=1);c=raw.loc[raw.index<=t].iloc[-1].close;pr=raw.loc[raw.index<=past].iloc[-1].close;assert abs((c/pr-1)*100-z['return60_pct'])<1e-9
   assert len(ev)==daily.total.sum();counts={k:int(ev[k].sum()) for k in ['trend','breakout','rebound']};counts['other']=int((~ev[['trend','breakout','rebound']].any(axis=1)).sum());assert not ev.time_utc.duplicated().any();audit={'month':month,'source':'new measurement','minute_rows_in_month':days*1440,'events':len(ev),'independent_pulse_checks_all_thresholds':scalar_checks,'independent_event_returns_checked':len(ev),'prefix_checks':3,'integrity':'PASS','condition_bars':condition,'crossings':crossings,'suppressed_crossings':crossings-len(ev)};origin=month
  item={'month':month,'days':days,'events':len(ev),'events_per_day':len(ev)/days,'days_with_events':int((daily.total>0).sum()),'flags':counts,'exclusive':{k:int((ev.category==k).sum()) for k in ['rebound','breakout','trend','other']},'sensitivity':ss,'origin':origin};allrows.append(item);audits.append(audit);dump(out/'summary.json',item);print(month,len(ev),counts,flush=True)
 metrics=[]
 for k in ['trend','breakout','rebound','other']:
  perday=np.array([z['flags'][k]/z['days'] for z in allrows]);share=np.array([z['flags'][k]/z['events'] for z in allrows]);metrics.append({'flag':k,'name':NAMES[k],'total_count':sum(z['flags'][k] for z in allrows),'per_day_mean':float(perday.mean()),'per_day_min':float(perday.min()),'per_day_max':float(perday.max()),'per_day_cv':float(perday.std(ddof=0)/perday.mean()),'share_mean':float(share.mean()),'share_min':float(share.min()),'share_max':float(share.max()),'share_cv':float(share.std(ddof=0)/share.mean())})
 result={'registration':reg,'source_sha256':expected,'months':allrows,'metrics':metrics,'total_events':sum(z['events'] for z in allrows),'total_days':sum(z['days'] for z in allrows),'per_day_rank':[m['flag'] for m in sorted(metrics,key=lambda z:z['per_day_cv'])],'share_rank':[m['flag'] for m in sorted(metrics,key=lambda z:z['share_cv'])],'audits':audits,'compute_seconds':time.monotonic()-started,'status':'descriptive recurrence only; no predictive accuracy or causal inference'};dump(P/'summary.json',result)
 pd.DataFrame([{'month':z['month'],'days':z['days'],'events':z['events'],'events_per_day':z['events_per_day'],'days_with_events':z['days_with_events'],**{k+'_count':v for k,v in z['flags'].items()},**{k+'_share':v/z['events'] for k,v in z['flags'].items()}} for z in allrows]).to_csv(P/'monthly_comparison.csv',index=False);pd.DataFrame(metrics).to_csv(P/'stability_metrics.csv',index=False);print(json.dumps(metrics,ensure_ascii=False,indent=2))
if __name__=='__main__':run()
