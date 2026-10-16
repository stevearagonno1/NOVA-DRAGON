"""Encode the Lead's full reading of three complete, source-verified segments."""
import json,hashlib
from pathlib import Path
import semantic_pipeline as p
R=Path(__file__).resolve().parent;w=R/'execution';selected=json.loads((R/'REVIEW-SELECTION.json').read_text());reviews=[];nodes=[];edges=[];findings=[]
assert selected[0]['text']==selected[1]['text']
def add(s,key,label,relation,quote,meaning,confidence='EXTRACTED'):
 assert quote in s['text']
 target=p.gid(s['source_file']+'#semantic:'+key)
 nodes.append({'id':target,'label':label,'file_type':'semantic_definition','source_file':s['source_file'],'meaning':meaning})
 e={'source':p.gid(s['source_file']),'target':target,'relation':relation,'confidence':confidence,'confidence_score':1.0 if confidence=='EXTRACTED' else 0.95,'source_file':s['source_file'],'segment_id':s['segment_id'],'evidence_quote':quote}
 if confidence!='EXTRACTED':e['rationale']=meaning
 edges.append(e)
for s in selected:
 isgen=s['source_file'].endswith('generate-independent.py')
 summary=('Exports complete independent parameter records. Modes list, changes, custom and cartesian use the base versions and SQL views. Overrides require known base parameters and nonempty lists. Unknown/open axes remain frozen. SHA256 identity includes family, definition, parameters, signal, timing and asset. Cartesian counts enumerate settings, not runnable indicators or market tests. The registered branch is unreachable because argparse choices omit registered. Count-only reports Cartesian product size before applying limit. Default DB is a sibling path; dependencies are not validated.' if isgen else 'Acquires pinned monthly minute archives, checks each hash and contiguous timestamps, aggregates 1/5/15/60-minute frames. Streaming SMA-seeded EMA/Wilder averages compute 14 measurements; lagged comparisons use five bars and volume uses the preceding 60 bars. Flat RSI becomes 50, zero loss becomes 100. Monthly binary records are little-endian int64 plus14 float64. Compute consumes preceding input for warmup and asserts200 prior bars before writing. It explicitly produces no future labels or parameter variants. latest selects only a completed higher-frame bar at the decision time. Static source review establishes intended code behavior, not execution success or market efficacy.')
 reviews.append({'segment_id':s['segment_id'],'read_complete':True,'summary':summary,'review_method':'Lead read entire segment; identical generator copy verified byte-for-byte','text_sha256':hashlib.sha256(s['text'].encode()).hexdigest()})
 if isgen:
  add(s,'settings-validity','Parameter combinations remain unvalidated','declares_limitation',"'validity':'parameter choices only; dependencies and runtime not validated'",'A generated configuration is not evidence of a working runtime or a profitable signal.')
  add(s,'catalog-view','Independent indicator SQL catalog','reads_view',"sql='SELECT * FROM independent_indicator_catalog'",'Changes mode consumes the view, preserving full independent configurations.')
  add(s,'open-axes','Unknown axes are frozen','defines_behavior',"if v is None:frozen.append(a['name']);continue",'No value is invented for an axis without known choices.')
  add(s,'identity','Configuration-specific identity','defines_identity',"identity=[base['family'],base['definition_id'],p,base['signal'],base['timing'],base['asset']]",'Settings, timing and signal participate in the identity; display names alone do not merge variants.')
  add(s,'unreachable-registered','Registered mode unreachable from CLI','has_static_defect',"p.add_argument('--mode',choices=['list','changes','custom','cartesian'],default='list')",'The complete source contains elif args.mode==registered, but argparse rejects that value. This is a static control-flow finding; no market experiment was run.','INFERRED')
  findings.append({'source_file':s['source_file'],'type':'CLI_CHOICE_MISMATCH','evidence':["p.add_argument('--mode',choices=['list','changes','custom','cartesian'],default='list')","elif args.mode=='registered':"],'status':'STATICALLY_CONFIRMED_NOT_REPAIRED','impact':'Registered export branch cannot be selected through this CLI; other modes are not thereby proven broken.'})
 else:
  for key,label,quote,meaning in [
   ('frames','Four candle frames','FRAMES=[1,5,15,60]','Frame durations in minutes, not four parameter variants.'),
   ('atr','ATR14 Wilder','self.atr=Average(14,True)','True range uses previous close, smoothed with Wilder14.'),
   ('ema','EMA20','self.ema=Average(20)','Seed is the mean of first20 closes; subsequent alpha2/21.'),
   ('macd','MACD12/26/9','self.fast=Average(12);self.slow=Average(26);self.signal=Average(9)','EMA12 minus EMA26; signal EMA9; normalized histogram and histogram change are also emitted.'),
   ('rsi','RSI14 Wilder','self.gain=Average(14,True);self.loss=Average(14,True)','Wilder gains/losses; flat series50, zero loss100.'),
   ('volume','Volume preceding60 bars','div(v,sum(self.vol)/60) if len(self.vol)==60 else math.nan','Current volume appended after ratio computation; baseline excludes current bar.'),
   ('record','120-byte feature record',"RECORD=struct.Struct('<q14d')",'Open time int64 and14float64, little endian.'),
   ('closed-bar','Only completed frame at decision','target=(at//(frame*60000)-1)*frame*60000','Target open is preceding fully closed frame. This does not prove all downstream consumers avoid lookahead.'),
   ('scope','Calculation only',"'future_labels_computed':False,'parameter_variants':0,'calculation_only':True",'No future outcome labels, no setting sweep and no market signal accuracy test in this producer.')]:add(s,key,label,'defines_behavior',quote,meaning)
(w/'fragments').mkdir(exist_ok=True)
p.write(w/'fragments'/'00001-core-semantics.json',{'reviews':reviews,'nodes':nodes,'edges':edges})
p.write(w/'CORE-SEMANTIC-FINDINGS.json',{'source_commit':p.PIN,'complete_segments':len(reviews),'relations':len(edges),'findings':findings,'all_repository_semantics_complete':False})
print('Reviewed segments',len(reviews),'semantic relations',len(edges))
