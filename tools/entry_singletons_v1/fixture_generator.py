"""Deterministic synthetic minute fixture; yields rows directly, never writes candles."""
import hashlib, math, struct
from datetime import datetime, timezone
from .classify import read_rows

GENERATOR_VERSION='singleton-fixture-sines-v2'
SEED=20261008
START=int(datetime(2026,6,1,tzinfo=timezone.utc).timestamp())
DAYS=61
ASSET_PHASE={'BTC':0.0,'ETH':0.7,'SOL':1.4}

def _iter(asset,days=DAYS):
 if asset not in ASSET_PHASE:raise ValueError('asset outside fixed universe')
 phase=ASSET_PHASE[asset]+(SEED%997)/997.0
 previous=100.0+('BTC','ETH','SOL').index(asset)*35
 for k in range(days*1440):
  ts=START+k*60
  close=100.0+('BTC','ETH','SOL').index(asset)*35+0.000025*k+2.2*math.sin(k/1210+phase)+1.35*math.sin(k/89+phase/3)+0.45*math.sin(k/17+phase/2)
  spread=0.015+0.025*(1+math.sin(k/11+phase))
  op=previous;high=max(op,close)+spread;low=min(op,close)-spread
  volume=10+3*abs(math.sin(k/7+phase))+2*abs(math.cos(k/41+phase))
  yield {'time':ts,'open':op,'high':high,'low':low,'close':close,'volume':volume}
  previous=close

def build_fixture(asset,days=DAYS):
 """Build one asset in memory and fingerprint canonical timestamp/OHLCV bytes."""
 digest=hashlib.sha256()
 def stream():
  for r in _iter(asset,days):
   digest.update(struct.pack('>q5d',r['time'],r['open'],r['high'],r['low'],r['close'],r['volume']))
   yield r
 rows=read_rows(stream())
 return rows,digest.hexdigest()

def specification(days=DAYS):
 if not 2<=days<=DAYS:raise ValueError('fixture days outside fixed synthetic bounds')
 return {'generator':GENERATOR_VERSION,'seed':SEED,'start_utc':'2026-06-01T00:00:00Z','days':days,'minutes_per_asset':days*1440,'assets':['BTC','ETH','SOL'],'synthetic':True,'market_run':False,'serialization':'big-endian int64 unix seconds + five IEEE754 binary64 OHLCV values'}
