#!/usr/bin/env python3
"""Export independent indicator configurations. Repository code is never executed."""
import argparse,sqlite3,json,itertools,hashlib,pathlib,sys,math
J=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def custom_record(base,p,origin):
 identity=[base['family'],base['definition_id'],p,base['signal'],base['timing'],base['asset']]
 return {**base,'id':'GENERATED-'+hashlib.sha256(J(identity).encode()).hexdigest(),'settings':p,'origin':origin,'validity':'parameter choices only; dependencies and runtime not validated'}
def read_base(c,i):
 r=c.execute('SELECT * FROM versions WHERE id=?',(i,)).fetchone()
 if r is None:raise ValueError('Unknown base_id: '+i)
 r=dict(r);r['settings']=json.loads(r['settings']);r['sources']=json.loads(r['sources']);return r
def choices(a,custom):
 if a['name'] in custom:
  x=custom[a['name']]
  if not isinstance(x,list) or not x:raise ValueError('Each custom parameter must have a nonempty JSON list')
  return x
 if a['kind']=='integer_interval':return range(a['lo'],a['hi']+1)
 if a['values_json'] is not None:return json.loads(a['values_json'])
 return None

def main():
 p=argparse.ArgumentParser(description='Every output row is an independent full configuration.')
 p.add_argument('--db',default=str(pathlib.Path(__file__).with_name('NOVA-separated.sqlite')))
 p.add_argument('--mode',choices=['list','changes','custom','cartesian'],default='list')
 p.add_argument('--family');p.add_argument('--base');p.add_argument('--values-json',help='JSON mapping parameter name to a list of chosen values')
 p.add_argument('--output');p.add_argument('--limit',type=int,help='Optional explicit output limit; no limit is applied by default')
 p.add_argument('--count-only',action='store_true')
 args=p.parse_args();c=sqlite3.connect(args.db);c.row_factory=sqlite3.Row
 out=open(args.output,'w',encoding='utf-8') if args.output else sys.stdout
 emitted=0
 def emit(r):
  nonlocal emitted
  if args.limit is not None and emitted>=args.limit:return False
  if not args.count_only:out.write(J(r)+'\n')
  emitted+=1;return True
 if args.mode=='list':
  sql='SELECT id,family,origin,settings FROM versions';values=[]
  if args.family:sql+=' WHERE family=?';values=[args.family]
  for row in c.execute(sql,values):
   r=dict(row);r['settings']=json.loads(r['settings'])
   if not emit(r):break
 elif args.mode=='registered':
  for row in c.execute('SELECT * FROM independent_combinations'):
   r=dict(row);r['configuration']=json.loads(r.pop('full_configuration'))
   if not emit(r):break
 elif args.mode=='changes':
  sql='SELECT * FROM independent_indicator_catalog';where=[];values=[]
  if args.family:where.append('family=?');values.append(args.family)
  if args.base:where.append('(id=? OR base_id=?)');values.extend([args.base,args.base])
  if where:sql+=' WHERE '+' AND '.join(where)
  for row in c.execute(sql,values):
   r=dict(row);r['settings']=json.loads(r['settings']);r['sources']=json.loads(r['sources'])
   if not emit(r):break
 else:
  if not args.base:p.error('--base is required for custom/cartesian')
  b=read_base(c,args.base);custom=json.loads(args.values_json or '{}')
  if not isinstance(custom,dict):p.error('--values-json must be an object')
  for name in custom:
   if name not in b['settings']:p.error('Unknown parameter: '+name)
  aa=[dict(x) for x in c.execute('SELECT * FROM parameter_axes WHERE base_id=? ORDER BY id',(args.base,))]
  if args.mode=='custom':aa=[]
  names=[];vals=[];frozen=[]
  for a in aa:
   v=choices(a,custom)
   if v is None:frozen.append(a['name']);continue
   names.append(a['name']);vals.append(v)
  for name,value in custom.items():
   if name in names:continue
   if not isinstance(value,list) or not value:p.error('Custom choices must be nonempty lists')
   names.append(name);vals.append(value)
  count=math.prod(len(v) for v in vals)
  print(J({'cartesian_count':count,'frozen_open_or_unknown_parameters':frozen,'status':'unvalidated Cartesian parameter combinations'}),file=sys.stderr)
  if args.count_only:print(J({'count':count}));return
  for vv in itertools.product(*vals):
   params={**b['settings'],**dict(zip(names,vv))};r=custom_record(b,params,'independent_cartesian_unvalidated');r['frozen_parameters']=frozen
   if not emit(r):break
 if args.count_only:print(J({'count':emitted}))
 else:print(J({'emitted':emitted,'explicit_limit':args.limit}),file=sys.stderr)
 if args.output:out.close()
 c.close()
if __name__=='__main__':main()
