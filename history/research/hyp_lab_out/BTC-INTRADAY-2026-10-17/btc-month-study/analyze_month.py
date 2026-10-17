from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,time,sys
P=Path(__file__).parent
NAMES={'rebound':'صعود بعد ضعف أو تشبع بيعي سابق','breakout':'اختراق قمة آخر3ساعات','trend':'استمرار اتجاه صاعد','other':'صعود آخر دون الشروط الثلاثة'}
def features(b):
 x=b.copy();c=x.close;delta=c.diff();g=delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean();l=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean();x['rsi14']=(100-100/(1+g/l)).where(l!=0,100).where((g!=0)|(l!=0),50)
 x['ema20']=c.ewm(span=20,adjust=False,min_periods=20).mean();x['ema50']=c.ewm(span=50,adjust=False,min_periods=50).mean();x['return60_pct']=(c/c.shift(4)-1)*100;x['price60_before']=c.shift(4);x['prior_return60_pct']=(c.shift(4)/c.shift(8)-1)*100
 x['prior_rsi_min']=x.rsi14.shift().rolling(4).min();x['prior_high3h']=x.high.shift().rolling(12).max();x['volume60']=x.volume.rolling(4).sum();x['volume_previous60']=x.volume.shift(4).rolling(4).sum();x['volume_ratio']=x.volume60/x.volume_previous60
 x['rebound']=(x.prior_rsi_min<=30)|(x.prior_return60_pct<=-.5);x['breakout']=c>x.prior_high3h;x['trend']=(x.ema20>x.ema50)&(c>x.ema20)
 dates=pd.Series(x.index.tz_convert('Asia/Aden').date,index=x.index);good=x['minutes'].eq(15)
 x['eligible']=(dates==dates.shift(4))&(good.rolling(61).sum()==61)&x.rsi14.notna()&x.ema50.notna();return x
def accepted(x,threshold,month):
 local=x.index.tz_convert('Asia/Aden');inmonth=(local.strftime('%Y-%m')==month);raw=x.return60_pct.ge(threshold)&x.eligible&inmonth;pulse=raw&~raw.shift(fill_value=False);out=[];last=None
 for t in x.index[pulse]:
  if last is None or (t-last).total_seconds()>=3600:out.append(t);last=t
 return out,int(raw.sum()),int(pulse.sum())
def main():
 started=time.monotonic();reg=json.loads((P/'registration.json').read_text());month=reg['month'];start=pd.Timestamp(month+'-01',tz='Asia/Aden');end=start+pd.offsets.MonthBegin();src=P/'BTCUSDT_1m.parquet'
 if src.exists():
  digest=hashlib.sha256(src.read_bytes()).hexdigest();assert digest.startswith('e321e4ad7d4ccda6'),digest
  raw=pd.read_parquet(src,engine='fastparquet');t=raw.open_time.to_numpy(np.int64);t=np.where(t>1e14,t//1000,t);raw.index=pd.to_datetime(t,unit='ms',utc=True);raw=raw.loc[(raw.index>=start.tz_convert('UTC')-pd.Timedelta(days=4))&(raw.index<end.tz_convert('UTC'))].copy();raw.to_csv(P/'source_minutes.csv',index_label='time_utc',float_format='%.17g')
 else:
  raw=pd.read_csv(P/'source_minutes.csv',index_col='time_utc');raw.index=pd.to_datetime(raw.index,utc=True);digest=json.loads((P/'source_manifest.json').read_text())['source_sha256']
 assert not raw.index.duplicated().any();assert np.all(np.diff(raw.index.asi8)==60*10**9),'minute gap';assert np.isfinite(raw[['open','high','low','close','volume']]).all().all();assert ((raw.low<=raw[['open','close']].min(axis=1))&(raw.high>=raw[['open','close']].max(axis=1))&(raw.low>0)&(raw.volume>=0)).all()
 b=raw.resample('15min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),volume=('volume','sum'),minutes=('close','count'));b.index=b.index+pd.Timedelta(minutes=15)-pd.Timedelta(milliseconds=1);assert b.minutes.eq(15).all();x=features(b);ts,raw_n,pulse_n=accepted(x,.5,month);rows=[]
 for i,t in enumerate(ts):
  z=x.loc[t];kind=next((k for k in ['rebound','breakout','trend'] if bool(z[k])),'other');local=t.tz_convert('Asia/Aden')
  rows.append({'event':i+1,'time_aden':local.isoformat(),'time_utc':t.isoformat(),'day':str(local.date()),'category':kind,'category_ar':NAMES[kind],**{k:float(z[k]) for k in ['close','price60_before','return60_pct','prior_return60_pct','rsi14','prior_rsi_min','ema20','ema50','prior_high3h','volume60','volume_previous60','volume_ratio']},**{k:bool(z[k]) for k in ['rebound','breakout','trend']}})
 events=pd.DataFrame(rows);events.to_csv(P/'events.csv',index=False,float_format='%.12g');x.to_csv(P/'bars15m.csv',index_label='close_time_utc',float_format='%.12g')
 days=pd.DataFrame({'day':pd.date_range(start,end,inclusive='left').strftime('%Y-%m-%d')});daily=events.groupby(['day','category']).size().unstack(fill_value=0).reindex(columns=NAMES,fill_value=0).reset_index() if len(events) else pd.DataFrame(columns=['day',*NAMES]);daily=days.merge(daily,on='day',how='left').fillna(0);daily['total']=daily[list(NAMES)].sum(axis=1).astype(int);daily.to_csv(P/'daily_counts.csv',index=False)
 counts=events.category.value_counts().reindex(NAMES,fill_value=0).astype(int).to_dict() if len(events) else dict.fromkeys(NAMES,0);flags={k:int(events[k].sum()) for k in ['rebound','breakout','trend']};sensitivity=[]
 for threshold in reg['sensitivity_thresholds_pct']:
  tt,nn,pp=accepted(x,threshold,month);sensitivity.append({'threshold_pct':threshold,'events':len(tt),'days':len(set(t.tz_convert('Asia/Aden').date() for t in tt)),'condition_bars':nn,'crossings':pp})
 # Prefix reconstruction confirms snapshot values and event timing do not need later candles.
 prefixchecks=[]
 for day in [7,15,23]:
  cutoff=pd.Timestamp(f'{month}-{day:02d} 23:59:59.999',tz='Asia/Aden').tz_convert('UTC');part=features(b.loc[b.index<=cutoff]);a,_,_=accepted(part,.5,month);assert a==[t for t in ts if t<=cutoff];cols=['return60_pct','rsi14','ema20','ema50','volume_ratio','prior_high3h'];assert np.allclose(part[cols],x.loc[part.index,cols],equal_nan=True);prefixchecks.append(str(cutoff))
 for row in rows:
  t=pd.Timestamp(row['time_utc']);earlier=t-pd.Timedelta(hours=1);assert t.tz_convert('Asia/Aden').date()==earlier.tz_convert('Asia/Aden').date();current=raw.loc[raw.index<=t].iloc[-1].close;past=raw.loc[raw.index<=earlier].iloc[-1].close;assert abs((current/past-1)*100-row['return60_pct'])<1e-9
 assert daily.total.sum()==len(events)==sum(counts.values());assert all((b-a).total_seconds()>=3600 for a,b in zip(ts,ts[1:]));assert not events.time_utc.duplicated().any()
 summary={'registration':reg,'source_sha256':digest,'source_slice_rows':len(raw),'month_minute_rows':int(((raw.index>=start)&(raw.index<end)).sum()),'events':len(events),'days_with_events':int((daily.total>0).sum()),'days_zero':int((daily.total==0).sum()),'category_counts':counts,'overlapping_flag_counts':flags,'condition_bars':raw_n,'crossings':pulse_n,'suppressed_crossings':pulse_n-len(events),'sensitivity':sensitivity,'prefix_checks':prefixchecks,'audit':'PASS','scalar_return_checks':len(rows),'compute_seconds':time.monotonic()-started,'limitations':'one randomly selected month; contemporaneous descriptive state, not future predictive accuracy, profitability or causal explanation'}
 (P/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
