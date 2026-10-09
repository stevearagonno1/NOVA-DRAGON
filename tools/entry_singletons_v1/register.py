"""Closed deterministic candidate registry. No data or runtime search."""
from itertools import product
import json
from pathlib import Path

FAMILIES = {
 'RSI_LEVEL': {'n':[7,14,21,28], 't':[20,30,40,50,60]},
 'STOCH_LEVEL': {'n':[7,14,21,28], 't':[20,30,50]},
 'STOCH_KD': {'n':[7,14,21,28], 'd':[3,5,9], 't':[20,30,50]},
 'CCI_LEVEL': {'n':[7,14,21,28], 't':[-200,-150,-100,0]},
 'WILLIAMS_LEVEL': {'n':[7,14,21,28], 't':[-90,-80,-60,-50]},
 'MFI_LEVEL': {'n':[7,14,21,28], 't':[20,30,50]},
 'CMF_LEVEL': {'n':[10,20,40], 't':[0,0.05,0.10]},
 'PRICE_EMA': {'n':[5,10,20,30,50]},
 'EMA_CROSS': {'fast':[5,10,20], 'slow':[20,30,50,100]},
 'MACD_CROSS': {'fast':[5,8,12], 'slow':[17,26,35], 'signal':[5,9]},
 'BB_RECLAIM_BREAK': {'n':[10,20,30], 'k':[1.5,2,2.5], 'mode':['LOWER','UPPER']},
 'DONCHIAN': {'n':[10,20,40], 'mode':['UPPER','MID']},
 'ROC_LEVEL': {'n':[3,6,12,24], 't':[0,0.5,1,2]},
 'AROON_CROSS': {'n':[14,25,50]},
 'OBV_EMA': {'n':[5,10,20,40]},
 'RVOL_STATE': {'n':[10,20,40], 't':[1.2,1.5,2,3]},
 'ADX_DIRECTION': {'n':[7,14,28], 't':[15,20,25,30]},
}
EXPECTED = {'RSI_LEVEL':20,'STOCH_LEVEL':12,'STOCH_KD':36,'CCI_LEVEL':16,'WILLIAMS_LEVEL':16,'MFI_LEVEL':12,'CMF_LEVEL':9,'PRICE_EMA':5,'EMA_CROSS':11,'MACD_CROSS':18,'BB_RECLAIM_BREAK':18,'DONCHIAN':6,'ROC_LEVEL':16,'AROON_CROSS':3,'OBV_EMA':4,'RVOL_STATE':12,'ADX_DIRECTION':12}

def build_registry():
 out=[]
 for family, axes in FAMILIES.items():
  names=list(axes); vals=[axes[k] for k in names]
  for tup in product(*vals):
   p=dict(zip(names,tup))
   if family=='EMA_CROSS' and p['fast']>=p['slow']: continue
   out.append({'setting_id':family+'__'+'__'.join(f'{k}-{p[k]}' for k in names),'family':family,'params':p,
    'signal_definition':{'RSI_LEVEL':'CrossingLevel(RSI(n),t)','STOCH_LEVEL':'CrossingLevel(K(n),t)','STOCH_KD':'CrossUp(K(n),SMA(K,d)) and K<=t','CCI_LEVEL':'CrossingLevel(CCI(n),t)','WILLIAMS_LEVEL':'CrossingLevel(WilliamsR(n),t)','MFI_LEVEL':'CrossingLevel(MFI(n),t)','CMF_LEVEL':'CrossingLevel(CMF(n),t)','PRICE_EMA':'CrossUp(C,EMA(n))','EMA_CROSS':'CrossUp(EMA(fast),EMA(slow))','MACD_CROSS':'CrossUp(MACD_line,signal_line)','BB_RECLAIM_BREAK':'CrossUp(C,lower/upper band by mode)','DONCHIAN':'UPPER: C>prior n-bar max H; MID: CrossUp(C,prior-channel midpoint)','ROC_LEVEL':'CrossingLevel(ROC(n),t)','AROON_CROSS':'CrossUp(AroonUp,AroonDown)','OBV_EMA':'CrossUp(OBV,EMA(OBV,n))','RVOL_STATE':'V/mean(previous n V)>=t','ADX_DIRECTION':'ADX>=t and rising and +DI>-DI'}[family]})
 assert len(out)==226 and {f:sum(x['family']==f for x in out) for f in EXPECTED}==EXPECTED
 return out

def write_registry(path=None):
 path=Path(path) if path else Path(__file__).with_name('registry.json')
 path.write_text(json.dumps(build_registry(),indent=2,sort_keys=True)+'\n')
 return path
if __name__=='__main__': write_registry()
