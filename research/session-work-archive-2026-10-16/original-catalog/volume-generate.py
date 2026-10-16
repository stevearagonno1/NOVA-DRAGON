#!/usr/bin/env python3
import argparse,sqlite3,pathlib,json,hashlib,itertools,sys
J=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def decode(spec,idx):
 axes=spec['axes'];p=dict(spec['constant_settings']);q=idx
 for a in reversed(axes):
  d=a['domain'];n=len(d['values']) if d['kind']=='finite_values' else d['maximum']-d['minimum']+1;q,k=divmod(q,n);p[a['parameter']]=d['values'][k] if d['kind']=='finite_values' else d['minimum']+k
 if q:raise ValueError('Index exceeds space size')
 return p

def main():
 p=argparse.ArgumentParser(description='Every finite volume configuration has an independent indexed ID and full settings.')
 p.add_argument('--export-materialized',action='store_true');p.add_argument('--db',default=str(pathlib.Path(__file__).with_name('NOVA-separated.sqlite')));p.add_argument('--list',action='store_true');p.add_argument('--space');p.add_argument('--index',type=int);p.add_argument('--start',type=int,default=0);p.add_argument('--stop',type=int);p.add_argument('--bind-json',default='{}');p.add_argument('--bar-count',type=int,help='Enumerate all start<=end bar-coordinate pairs for FRVP in a concrete N-bar dataset');p.add_argument('--output');p.add_argument('--count-only',action='store_true')
 a=p.parse_args();c=sqlite3.connect(a.db);c.row_factory=sqlite3.Row
 if a.export_materialized:
  out=open(a.output,'w',encoding='utf-8') if a.output else sys.stdout
  for row in c.execute('SELECT * FROM volume_versions'):
   v=dict(row)
   for k in ['settings','sources','unresolved_parameters']:v[k]=json.loads(v[k])
   out.write(J(v)+'\n')
  if a.output:out.close()
  return
 if a.list:
  for r in c.execute('SELECT id,base_id,family,count,materialized FROM volume_spaces ORDER BY family'):print(J(dict(r)))
  return
 if not a.space:p.error('--space is required unless --list')
 r=c.execute('SELECT * FROM volume_spaces WHERE id=?',(a.space,)).fetchone()
 if r is None:p.error('Unknown space identifier')
 r=dict(r);spec=json.loads(r['spec']);count=int(r['count']);b=dict(c.execute('SELECT * FROM versions WHERE id=?',(r['base_id'],)).fetchone());b['settings']=json.loads(b['settings']);b['sources']=json.loads(b['sources']);bind=json.loads(a.bind_json)
 if not isinstance(bind,dict):p.error('--bind-json must be an object')
 start=a.index if a.index is not None else a.start;stop=start+1 if a.index is not None else (count if a.stop is None else a.stop)
 if not 0<=start<=stop<=count:p.error('Require 0 <= start <= stop <= count')
 if a.bar_count is not None and (a.bar_count<=0 or ':FRVP:' not in r['family']):p.error('--bar-count requires positive N and an FRVP space')
 pairs=a.bar_count*(a.bar_count+1)//2 if a.bar_count else 1
 if a.count_only:print(J({'space_total':count,'requested_indices':stop-start,'coordinate_pairs_per_index':pairs,'requested_rows':(stop-start)*pairs,'unresolved_axes':spec['open_or_unresolved_axes']}));return
 out=open(a.output,'w',encoding='utf-8') if a.output else sys.stdout;emitted=0
 for idx in range(start,stop):
  params=decode(spec,idx);coords=((i,j) for i in range(a.bar_count) for j in range(i,a.bar_count)) if a.bar_count else [None]
  for pair in coords:
   effective={**params,**bind}
   if pair is not None:effective.update(start_bar=pair[0],end_bar=pair[1])
   if isinstance(effective.get('start_bar'),int) and isinstance(effective.get('end_bar'),int) and effective['start_bar']>effective['end_bar']:p.error('start_bar must not exceed end_bar')
   if isinstance(effective.get('row_size'),(int,float)) and effective['row_size']<=0:p.error('row_size must be positive')
   if isinstance(effective.get('value_area_percent'),(int,float)) and not 0<=effective['value_area_percent']<=100:p.error('value-area percent must be in0..100')
   extension={**bind,**({'start_bar':pair[0],'end_bar':pair[1]} if pair else {})};suffix='-B-'+hashlib.sha256(J(extension).encode()).hexdigest() if extension else ''
   unresolved=[k for k,v in effective.items() if isinstance(v,dict) and (v.get('unresolved') or 'expression' in v)]
   output={**b,'id':r['id']+'-C-'+str(idx)+suffix,'settings':effective,'origin':'volume_cartesian_bound' if extension else 'declared_volume_cartesian_unvalidated','unresolved_parameters':unresolved,'scope':spec['scope'],'validity':'not runtime-tested; unresolved fields and source-dependent constraints apply'}
   out.write(J(output)+'\n');emitted+=1
 if a.output:out.close()
 print(J({'emitted':emitted}),file=sys.stderr);c.close()
if __name__=='__main__':main()
