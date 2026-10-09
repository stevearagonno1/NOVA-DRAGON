"""Strict in-memory UTC OHLCV reader, causal aggregation, and exclusive states.
FOREIGN_SOURCE: state definitions audited against tools/percoin_states/pilot.py at 86304b62bf9c7d0914572e100892fac66f3f09dd.
"""
import csv, io, math
from datetime import datetime, timezone
from .indicators import ema, rsi, tr_atr
REQUIRED=('open_time_seconds','open','high','low','close','volume')

def normalize_open_time(value,unit):
 """Convert an explicitly declared integer epoch unit to UTC seconds without guessing."""
 try:x=int(value)
 except (TypeError,ValueError) as e:raise ValueError('open_time must be an integer epoch') from e
 scales={'seconds':1,'milliseconds':1000,'microseconds':1000000}
 if unit not in scales:raise ValueError('open_time unit must be seconds, milliseconds, or microseconds')
 scale=scales[unit]
 if x%scale:raise ValueError('open_time is not an exact whole second in its declared unit')
 sec=x//scale
 if sec%60:raise ValueError('open_time seconds are not minute aligned')
 return sec

def _validate(rows):
 out=[];last=None
 for line,row in enumerate(rows,2):
  try:
   if isinstance(row,dict):
    t=int(row.get('open_time_seconds',row.get('time')));o=float(row['open']);h=float(row['high']);l=float(row['low']);c=float(row['close']);v=float(row['volume'])
   else:
    t=int(row[0]);o,h,l,c,v=map(float,row[1:6])
  except Exception as e:raise ValueError(f'invalid in-memory numeric row {line}') from e
  vals=(o,h,l,c,v)
  if t%60:raise ValueError(f'timestamp not aligned to UTC minute at row {line}')
  if not all(math.isfinite(x) for x in vals) or min(o,h,l,c)<0 or v<0 or h<max(o,c,l) or l>min(o,c,h):raise ValueError(f'invalid OHLCV row {line}')
  if last is not None and t-last!=60:raise ValueError('duplicate or missing minute')
  out.append({'time':t,'open':o,'high':h,'low':l,'close':c,'volume':v});last=t
 if not out:raise ValueError('empty in-memory candle stream')
 return out

def read_rows(rows):
 """Validate the synthetic reader stream without materializing CSV or market files."""
 return _validate(rows)

def read_csv_text(text):
 """Optional strict schema check on a small in-memory CSV string; never reads disk."""
 r=csv.DictReader(io.StringIO(text))
 if tuple(r.fieldnames or ())!=REQUIRED:raise ValueError('CSV header must be exactly '+','.join(REQUIRED))
 return _validate(r)

def aggregate(rows,period):
 """Only complete UTC buckets containing every expected minute are returned."""
 out=[];current=None;expected=period//60
 for r in rows:
  bucket=(r['time']//period)*period
  if current is None or current['time']!=bucket:
   if current is not None and current['_count']==expected:out.append({k:v for k,v in current.items() if not k.startswith('_')})
   current={'time':bucket,'open':r['open'],'high':r['high'],'low':r['low'],'close':r['close'],'volume':r['volume'],'_count':1}
  else:
   current['high']=max(current['high'],r['high']);current['low']=min(current['low'],r['low']);current['close']=r['close'];current['volume']+=r['volume'];current['_count']+=1
 if current and current['_count']==expected:out.append({k:v for k,v in current.items() if not k.startswith('_')})
 return out

def classify(bars15,bars60):
 """At a 15m close use only the latest fully closed hourly candle."""
 n=len(bars15);labels=[None]*n;C=[b['close'] for b in bars15];H=[b['high'] for b in bars15];L=[b['low'] for b in bars15]
 e20=ema(C,20);r14=rsi(C,14);hc=[b['close'] for b in bars60];e20h=ema(hc,20);e50h=ema(hc,50);_,atr=tr_atr(bars60,14)
 j=0;hmap=[]
 for b in bars15:
  close_time=b['time']+900
  while j<len(bars60) and bars60[j]['time']+3600<=close_time:j+=1
  hmap.append(j-1)
 for i,b in enumerate(bars15):
  hi=hmap[i]
  if hi<0 or e20h[hi] is None or e50h[hi] is None or atr[hi] is None:continue
  up=e20h[hi]>e50h[hi] and hi>0 and e20h[hi-1] is not None and e20h[hi]>e20h[hi-1]
  breakout=False
  if i>=20 and atr[hi]>0:
   top=max(H[i-20:i]);bottom=min(L[i-20:i]);breakout=C[i]>top and top-bottom<=4*atr[hi]
  pull=False
  if up and i>=4 and e20[i] is not None and b['close']>b['open']:
   pull=any(e20[k] is not None and C[k]<=e20[k] for k in range(i-4,i)) and C[i]>e20[i]
  turn=False
  if not up and i>0 and r14[i] is not None and r14[i-1] is not None:
   turn=b['close']>b['open'] and C[i]>C[i-1] and r14[i]>r14[i-1]
  labels[i]='BREAKOUT' if breakout else 'PULLBACK' if pull else 'TURN' if turn else None
 return labels,atr,hmap

def iso(ts):return datetime.fromtimestamp(ts,tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
