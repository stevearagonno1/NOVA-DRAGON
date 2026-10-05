import importlib.util,subprocess,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('launcher',Path(__file__).parent/'tools/launch_stage1_checked.py')
L=importlib.util.module_from_spec(spec);spec.loader.exec_module(L)
class Gates(unittest.TestCase):
 def test_order(self):
  seen=[];L.gated_steps(seen.append);self.assertEqual(seen,['synthetic','measure','audit','delivery'])
 def test_preflight_only(self):
  seen=[];L.gated_steps(seen.append,True);self.assertEqual(seen,['synthetic'])
 def test_each_failure_stops_later_steps(self):
  for step in ['synthetic','measure','audit','delivery']:
   seen=[]
   def run(name):
    seen.append(name)
    if name==step:raise RuntimeError('fixture')
   with self.assertRaises(RuntimeError):L.gated_steps(run)
   self.assertEqual(seen[-1],step)
 def test_subprocess_failure_retains_actual_error(self):
  with tempfile.TemporaryDirectory() as d:
   def runner(*a,**kw):return subprocess.CompletedProcess(a,1,'','ModuleNotFoundError: fixture')
   with self.assertRaises(RuntimeError):L.run_checked('synthetic',[],{},Path(d),runner)
   self.assertIn('ModuleNotFoundError: fixture',(Path(d)/'synthetic.log').read_text())
unittest.main()
