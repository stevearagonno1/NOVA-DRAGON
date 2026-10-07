import unittest,tempfile,json,gzip
from pathlib import Path
import validate86 as V
import publish86 as P
from unittest.mock import patch
import zipfile,io
class Checks(unittest.TestCase):
 def test_frozen(self):
  f,p,g,k=V.registration();self.assertEqual(len(p),12);self.assertEqual(len(k),22);self.assertEqual(k[12][0],17312);self.assertEqual(len(g),12)
 def test_holm(self):
  self.assertEqual(V.holm([.01,.04,.03]),[.03,.06,.06]);self.assertEqual(V.holm([1,1,1]),[1,1,1])
 def test_rotations(self):
  mask=sum(1<<i for i in range(10,20));x=(1<<10)|(1<<15)
  for k in range(10):
   y=V.rotate(x,k,mask);self.assertEqual(y.bit_count(),2);self.assertEqual(V.rotate(y,(10-k)%10,mask),x)
 def test_gates(self):
  d={'signals':24,'matched_events':12,'precision':.5,'recall':.4,'macro_f1':.6,'per_asset':[{'signals':8,'events':10,'f1':.6}]*3};par=[{'macro_f1':.4,'per_asset':[{'f1':.4}]*3}]*2
  self.assertEqual(V.gate(d,.6,par,.2,.04)[0],'CONDITIONAL_TRANSFER_PASS');d['signals']=14;self.assertEqual(V.gate(d,.6,par,.2,.04)[0],'INSUFFICIENT_SAMPLE');d['signals']=24;self.assertEqual(V.gate(d,.6,par,.2,.06)[0],'NOT_CONFIRMED')
 def test_pipeline_resume_tamper(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);V.run(p,True,True);V.run(p,True);V.audit_only(p);before={q.name:q.read_bytes() for q in p.iterdir()};V.run(p,True);self.assertEqual(before,{q.name:q.read_bytes() for q in p.iterdir()})
   (p/'validation.json').write_text('{}')
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
   self.assertEqual(head,'f'*40);self.assertIn(P.DEST+'/frozen_selection.json',captured)
   with zipfile.ZipFile(io.BytesIO(captured[P.DEST+'/evidence.zip'])) as z:
    self.assertIn('validation.json',z.namelist());self.assertIn('alerts.json',z.namelist());self.assertEqual(json.loads(z.read('validation.json'))['cyclic_group_size'],131)
if __name__=='__main__':unittest.main()
