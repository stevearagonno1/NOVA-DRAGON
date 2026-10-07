import numpy as np

def definitions():
 return [{'kind':'HAMMER','ratio':r} for r in [2.,3.]]+[{'kind':'ENGULF','ratio':r} for r in [1.,1.25]]+[{'kind':'MORNING','recovery':r} for r in [.5,1.]]
def pattern(d,q,scalar=False):
 o,h,l,c=[np.asarray(d[k],float) for k in ['o','h','l','c']];N=len(c);body=abs(c-o);span=h-l;upper=h-np.maximum(o,c);lower=np.minimum(o,c)-l;truth=np.zeros(N,bool)
 for i in range(7,N):
  down=c[i-1]<c[i-7]
  if q['kind']=='HAMMER':v=body[i]>0 and span[i]>0 and lower[i]>=q['ratio']*body[i] and upper[i]<=body[i] and body[i]<=.35*span[i] and (c[i]-l[i])/span[i]>=.6
  elif q['kind']=='ENGULF':v=c[i-1]<o[i-1] and c[i]>o[i] and o[i]<=c[i-1] and c[i]>=o[i-1] and body[i]>=q['ratio']*body[i-1]
  else:v=c[i-2]<o[i-2] and span[i-2]>0 and body[i-2]>=.5*span[i-2] and body[i-1]<=.3*body[i-2] and c[i]>o[i] and span[i]>0 and body[i]>=.5*span[i] and c[i]>=c[i-2]+q['recovery']*body[i-2]
  truth[i]=down and v
 if scalar:
  ref=np.zeros(N,bool)
  for i in range(7,N):
   if not d['c'][i-1]<d['c'][i-7]:continue
   O,H,L,C=map(float,[d[k][i] for k in ['o','h','l','c']]);B=abs(C-O);S=H-L
   if q['kind']=='HAMMER':ref[i]=B>0 and S>0 and min(O,C)-L>=q['ratio']*B and H-max(O,C)<=B and B/S<=.35 and (C-L)/S>=.6
   elif q['kind']=='ENGULF':po,pc=float(d['o'][i-1]),float(d['c'][i-1]);ref[i]=pc<po and C>O and O<=pc and C>=po and B>=q['ratio']*abs(pc-po)
   else:
    po,pc,ph,pl=[float(d[k][i-2]) for k in ['o','c','h','l']];mid=abs(float(d['c'][i-1])-float(d['o'][i-1]));ref[i]=pc<po and ph>pl and po-pc>=.5*(ph-pl) and mid<=.3*(po-pc) and C>O and S>0 and B>=.5*S and C>=pc+q['recovery']*(po-pc)
  truth=ref
 return truth&~np.r_[False,truth[:-1]]

def signals(d,q,scalar=False):
 import signals88 as S
 a=pattern(d,q,scalar);mode=q['mode']
 if mode=='STANDALONE':return a
 name='CCI_21_-150' if q['asset']=='SOLUSDT' else 'CCI_14_-150';b=S.primitives(d,scalar)[name]
 if mode=='CCI_AND_CURRENT':truth=a&b
 elif scalar:truth=np.array([bool(a[i] and any(i-j>=0 and b[i-j] for j in [1,2])) for i in range(len(a))])
 else:truth=a&(np.r_[False,b[:-1]]|np.r_[False,False,b[:-2]])
 return truth&~np.r_[False,truth[:-1]]
