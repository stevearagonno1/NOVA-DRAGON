"""Independent CSV case and scalar forward-barrier reconciliation."""
from pathlib import Path
import csv,json,argparse,collections,sys
p=argparse.ArgumentParser();p.add_argument('--package',default='l0090/package');p.add_argument('--out',default='l0090/diagnosis');a=p.parse_args();root=Path(a.package);out=Path(a.out);x=json.loads((out/'diagnosis.json').read_text());alerts=list(csv.DictReader((out/'alerts.csv').open()));events=list(csv.DictReader((out/'events.csv').open()));count=0
for asset in x['per_asset']:
 bars=list(csv.DictReader((root/(asset+'.csv')).open()));close=[float(z['close']) for z in bars];high=[float(z['high']) for z in bars];low=[float(z['low']) for z in bars];atr=[];state=None
 for i in range(len(bars)):
  tr=max(high[i]-low[i],abs(high[i]-close[i-1]),abs(low[i]-close[i-1])) if i else high[i]-low[i];state=tr if state is None else state*13/14+tr/14;atr.append(state)
 claimed=set()
 for row in [r for r in alerts if r['asset']==asset]:
  i=int(row['bar']);period=int(row['period']);eligible=[e for e in events if e['asset']==asset and int(e['period'])==period and abs(i-int(e['onset']))<=2];match=next((e for e in eligible if (period,int(e['onset'])) not in claimed),None)
  classification='MATCHED' if match else 'DUPLICATE' if eligible else 'UNMATCHED';assert classification==row['classification']
  if match:claimed.add((period,int(match['onset'])))
  expected='NO_BARRIER';delay=''
  for k in range(i+1,i+25):
   if low[k]<=close[i]-atr[i]:expected='LOWER_FIRST';delay=str(k-i);break
   if high[k]>=close[i]+2*atr[i]:expected='UPPER_FIRST';delay=str(k-i);break
  assert expected==row['diagnostic_forward_barrier'] and delay==row['diagnostic_barrier_delay'];assert bars[i]['dt']==row['time'];count+=1
 s=x['per_asset'][asset];assert len(claimed)==s['matched_events'];assert sum(e['captured']=='False' for e in events if e['asset']==asset)==s['missed_events']
assert count==x['totals']['signals'];result={'status':'PASS','alert_classifications_and_scalar_barriers_checked':count,'event_rows_reconciled':len(events),'no_new_signal_test':True};(out/'independent-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
