import json,itertools,collections,re,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
parts=json.loads((R/'STATE-REVIEW-SELECTION.json').read_text());groups=collections.defaultdict(list)
for s in parts:groups[s['source_file']].append(s)
result=[];reference=None
for path,ss in groups.items():
 text=''.join(s['text'] for s in sorted(ss,key=lambda x:x['offset']))
 if path.endswith('.json'):
  d=json.loads(text);expected=[{'state_id':i,'signs':list(v)} for i,v in enumerate(itertools.product([-1,0,1],repeat=6))]
  assert d['states']==expected and d['state_count_per_frame']==729 and d['state_frame_cells']==2916 and d['frame_minutes']==[1,5,15,60]
  assert d['status']=='PROPOSED_NOT_MARKET_VALIDATED'
  if reference is None:reference=d
  else:assert d==reference
  result.append({'source':path,'checks':'all729 rows and IDs exhaustively matched to lexicographic ternary product; metadata equal across copies','status':'PASS_NUMERIC_SCHEMA_ONLY','text_sha256':hashlib.sha256(text.encode()).hexdigest()})
 else:
  rows=[]
  for line in text.splitlines():
   cells=[x.strip() for x in line.strip('|').split('|')]
   if len(cells)==7 and cells[0].isdigit():rows.append([int(x.replace('−','-')) for x in cells])
  assert rows==[[i,*v] for i,v in enumerate(itertools.product([-1,0,1],repeat=6))]
  result.append({'source':path,'status':'PASS_ALL729_TABLE_ROWS','prose_review':'Lead read prose excluding generated numeric rows; generated rows validated exhaustively, not claimed manually read. Definitions are proposed contexts, no order-book absorption/rebound/breakout classifier or market success proof.'})
(R/'execution'/'STATE-SCHEMA-REVIEW.json').write_text(json.dumps({'results':result,'semantic_full_read_flags_added':0,'market_validation':False},ensure_ascii=False,indent=2)+'\n')
print('PASS',len(result),'state dictionary copies; no market validation claim')
