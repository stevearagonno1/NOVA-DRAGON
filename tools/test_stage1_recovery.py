import importlib.util,json,os,signal,subprocess,sys,tempfile,time,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('recovery',Path(__file__).parent/'launch_stage1_recovery.py');R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)
class RecoveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  (self.root/'scope.json').write_text('{}');(self.root/'environment.json').write_text('{}');self.env=dict(os.environ)
 def tearDown(self):self.tmp.cleanup()
 def test_failure_records_actual_exit_and_output(self):
  with self.assertRaisesRegex(RuntimeError,'exit 7'):
   R.run_checked('measure',[sys.executable,'-c','import sys;print("actual failure",flush=True);sys.exit(7)'],self.env,self.root)
  state=json.loads(next((self.root/'supervision').glob('measure-*.json')).read_text());self.assertEqual(state['exit_code'],7)
  self.assertIn('actual failure',Path(state['log']).read_text())
 def test_synthetic_receipt_reused_only_same_fingerprint(self):
  cmd=[sys.executable,'-c','print("PASS")'];R.run_checked('synthetic',cmd,self.env,self.root)
  self.assertEqual(R.run_checked('synthetic',['missing-command'],self.env,self.root),'')
  (self.root/'scope.json').write_text('{"changed":1}')
  with self.assertRaises(FileNotFoundError):R.run_checked('synthetic',['missing-command'],self.env,self.root)
 def test_partial_output_and_secret_redaction(self):
  self.env['GH_TOKEN']='fixture-private-token'
  code='import os,sys,time;s=os.environ["GH_TOKEN"];sys.stdout.write(s[:8]);sys.stdout.flush();time.sleep(.1);print(s[8:]);print("finished")'
  R.run_checked('measure',[sys.executable,'-c',code],self.env,self.root,heartbeat=.03)
  text=next((self.root/'supervision').glob('*.log')).read_text();self.assertNotIn(self.env['GH_TOKEN'],text);self.assertIn('[REDACTED]',text)
 def test_sigkill_preserves_log_and_child_lock(self):
  # A real OS process is killed while its child is silent. No mock of death.
  launcher=str(Path(R.__file__).resolve());root=str(self.root)
  child_code='import time,sys;sys.stdout.write("BEFORE_DEATH");sys.stdout.flush();time.sleep(3)'
  setup=f'''import importlib.util,fcntl,os
from pathlib import Path
s=importlib.util.spec_from_file_location('r',{launcher!r});r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
f=open({str(self.root/'lock')!r},'a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);r.LOCK_FD=f.fileno()
r.run_checked('measure',[{sys.executable!r},'-c',{child_code!r}],dict(os.environ),Path({root!r}),heartbeat=.05)
'''
  parent=subprocess.Popen([sys.executable,'-c',setup],stdout=subprocess.DEVNULL,env={**os.environ,'GH_TOKEN':'fixture-private-token'})
  deadline=time.monotonic()+5;state=None
  while time.monotonic()<deadline:
   files=list((self.root/'supervision').glob('measure-*.json'))
   if files:
    state=json.loads(files[0].read_text())
    if state.get('pid') and 'BEFORE_DEATH' in Path(state['log']).read_text():break
   time.sleep(.02)
  self.assertIsNotNone(state);self.assertIn('BEFORE_DEATH',Path(state['log']).read_text())
  parent.kill();parent.wait()
  import fcntl
  with open(self.root/'lock','a') as f:
   with self.assertRaises(BlockingIOError):fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
   os.kill(state['pid'],signal.SIGTERM)
   deadline=time.monotonic()+5
   while time.monotonic()<deadline:
    try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);break
    except BlockingIOError:time.sleep(.05)
   else:self.fail('child lock did not release')
  self.assertEqual(json.loads(files[0].read_text())['status'],'RUNNING')
  # Unknown exit is not a recovery ban after no live child owns the lock.
  R.run_checked('measure',[sys.executable,'-c','print("RESUMED")'],self.env,self.root)
  self.assertTrue(any('RESUMED' in p.read_text() for p in (self.root/'supervision').glob('*.log')))

if __name__=='__main__':unittest.main()
