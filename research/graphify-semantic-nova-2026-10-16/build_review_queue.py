"""Deduplicate exact text for review without claiming unread text was reviewed."""
import json,gzip,hashlib,collections
from pathlib import Path
R=Path(__file__).resolve().parent;w=R/'execution';groups={};seen={}
for name in json.loads((w/'BATCH-MANIFEST.json').read_text()):
 for s in json.loads((w/'batches'/name).read_text()):
  h=hashlib.sha256(s['text'].encode()).hexdigest()
  g=groups.setdefault(h,{'text_sha256':h,'characters':len(s['text']),'representative':{'batch':name,'segment_id':s['segment_id']},'occurrences':[],'status':'PENDING_SEMANTIC_READING'})
  g['occurrences'].append({'batch':name,'segment_id':s['segment_id'],'source_file':s['source_file'],'offset':s['offset']})
reviews={r['segment_id']:r for f in (w/'fragments').glob('*.json') for r in json.loads(f.read_text())['reviews']}
for g in groups.values():
 g['explicitly_reviewed_segments']=[x['segment_id'] for x in g['occurrences'] if x['segment_id'] in reviews]
 if g['explicitly_reviewed_segments']:g['status']='HAS_COMPLETE_REVIEW_REUSE_REQUIRES_PROVENANCE_CHECK'
with gzip.open(w/'EXACT-TEXT-REVIEW-QUEUE.jsonl.gz','wt',encoding='utf-8') as f:
 for g in groups.values():f.write(json.dumps(g,ensure_ascii=False)+'\n')
summary={'segments':sum(len(g['occurrences']) for g in groups.values()),'unique_exact_text_groups':len(groups),'duplicate_occurrences':sum(len(g['occurrences'])-1 for g in groups.values()),'explicit_complete_reviews':len(reviews),'automatic_full_read_claims':0,'purpose':'Read identical text once while retaining every original path; not a replacement for semantic review.'}
(w/'REVIEW-QUEUE-SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
