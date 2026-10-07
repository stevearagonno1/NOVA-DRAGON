import unittest,tempfile,json,gzip
from pathlib import Path
import compare87 as V
import publish87 as P
from unittest.mock import patch
import zipfile,io
class Checks(unittest.TestCase):
 def test_frozen(self):
  f=V.load('selection87.json');self.assertEqual(f['shared']['selected'],17312);self.assertTrue(all(q['selected']==17312 for q in f['per_asset'].values()));self.assertFalse(f['validation_read'])
 def test_quality(self):
  row={'signals':120,'matched_events':90,'precision':.75,'recall':.5,'lag_median':0,'per_asset':[{'signals':40,'events':60,'precision':.75}]*3};self.assertEqual(V.quality(row)['status'],'QUALITY_CANDIDATE_ONLY');row['signals']=99;self.assertEqual(V.quality(row)['status'],'INSUFFICIENT_SAMPLE')
 def test_clusters_zero_and_identity(self):
  x=[[[10,5,10]]*12,[[6,4,10]]*12,[[10,8,10]]*12,[[6,4,10]]*12,[[6,4,10]]*12];d=V.infer(x,True);self.assertEqual(d['tests'][0]['status'],'CONDITIONAL_GAIN');self.assertEqual(d['tests'][1]['status'],'CONDITIONAL_GAIN');self.assertEqual(d['tests'][2]['status'],'IDENTICAL_FROZEN_POLICIES');zero=V.infer([[[0,0,0]]*4]*5,True);self.assertEqual(zero['tests'][0]['status'],'INSUFFICIENT_BLOCKS')
 def test_pipeline_resume_tamper(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);V.run(p,True,True);V.run(p,True);V.audit_only(p);before={q.name:q.read_bytes() for q in p.iterdir()};V.run(p,True);self.assertEqual(before,{q.name:q.read_bytes() for q in p.iterdir()})
   (p/'comparison.json').write_text('{}')
   with self.assertRaises(AssertionError):V.audit_only(p)
 def test_delivery_packager_actual_outputs(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);out=root/'outputs';V.run(out,True)
   # In-memory transport unit fixture only, never a remote market record.
   record=json.loads((out/'delivery.json').read_text());record['synthetic']=False;(out/'delivery.json').write_text(json.dumps(record))
   (root/'package_manifest.json').write_text('{}');captured={}
   def get(head,path):
    if path.endswith('package_manifest.json'):return b'{}'
    if path=='LOG.md':return b'unit fixture'
    raise RuntimeError('HTTP 404: unit fixture')
   def publish(files,message,expected):captured.update(files);return 'f'*40
   with patch.object(P,'api',return_value={'object':{'sha':'e'*40}}),patch.object(P,'get_file',side_effect=get),patch.object(P,'publish',side_effect=publish):
    head,receipt=P.complete(root,out,'unit-source')
   self.assertEqual(head,'f'*40);self.assertIn(P.DEST+'/selection87.json',captured)
   with zipfile.ZipFile(io.BytesIO(captured[P.DEST+'/evidence.zip'])) as z:
    self.assertIn('comparison.json',z.namelist());self.assertIn('alerts.json',z.namelist());self.assertEqual(json.loads(z.read('comparison.json'))['inference']['family'],3)
if __name__=='__main__':unittest.main()
