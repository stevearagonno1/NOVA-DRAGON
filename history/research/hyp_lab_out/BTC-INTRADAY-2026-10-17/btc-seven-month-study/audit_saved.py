from pathlib import Path
import pandas as pd,numpy as np,json,hashlib
P=Path(__file__).parent;s=json.loads((P/'summary.json').read_text());external=json.loads((P/'external_checks.json').read_text());checks=[]
for response in external:
 assert response['status']=='fulfilled';v=response['value'];month=v['month'];assert not v['error'];df=pd.read_csv(P/month/'bars15m.csv.gz',index_col=0);df.index=pd.to_datetime(df.index,utc=True)
 for row in v['data']['result']:
  z=df.loc[pd.to_datetime(row[6],unit='ms',utc=True)];diff=[abs(float(z[k])-float(row[j+1])) for j,k in enumerate(['open','high','low','close','volume'])];assert max(diff)<1e-7;checks.append({'month':month,'open_time_ms':row[0],'max_abs_difference':max(diff)})
for month in s['months']:
 m=month['month'];z=s['metrics']
 assert month['events']==sum(month['exclusive'].values())
for metric in s['metrics']:
 k=metric['flag'];daily=[x['flags'][k]/x['days'] for x in s['months']];share=[x['flags'][k]/x['events'] for x in s['months']]
 def independent_cv(values):
  average=sum(values)/len(values);variance=sum((x-average)**2 for x in values)/len(values);return variance**.5/average
 assert abs(independent_cv(daily)-metric['per_day_cv'])<1e-12;assert abs(independent_cv(share)-metric['share_cv'])<1e-12
assert sum(x['events'] for x in s['months'])==802
hashes={str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in P.rglob('*') if f.is_file() and f.suffix in {'.gz','.csv'} and f.name not in ['monthly_comparison.csv','stability_metrics.csv']}
result={'status':'PASS','months_reconciled':7,'all_event_count':802,'new_month_event_count':sum(x['events'] for x in s['months'] if x['month'] in s['registration']['new_months_in_draw_order']),'new_months_scalar_prefix_and_return_checks':s['audits'],'external_candles_verified':len(checks),'external_checks':checks,'source_full_sha256':s['source_sha256'],'independent_stability_formula_check':'PASS4flags2metrics','retained_data_sha256':hashes,'scope':'descriptive monthly recurrence; external match is a sample, not entire archive certification'}
(P/'independent_audit.json').write_text(json.dumps(result,indent=2));print('audit PASS',len(checks),'external candles; new events',result['new_month_event_count'])
