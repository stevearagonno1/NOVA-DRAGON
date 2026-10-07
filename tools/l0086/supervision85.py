"""Durable foreground supervision reused from checked L0084 recovery for L0085."""
import argparse,datetime,fcntl,hashlib,importlib.util,json,os
from pathlib import Path
import selectors,subprocess,sys,time,uuid
PIN='L0086-v1'
ORIGINAL_SHA='b534e24d98045da55ac167171bfdbd76d1ae39a9d0cbfcaf47d037c6b8119207'
LOCK_FD=None

def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def durable(path,data):
    temp=path.with_name(path.name+'.pending')
    with temp.open('w') as f:json.dump(data,f,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)
def fingerprint(root,env):
    observed=json.loads((root/'environment.json').read_text())
    stable={k:observed.get(k) for k in ('python','versions')}
    return hashlib.sha256((root/'scope.json').read_bytes()+json.dumps(stable,sort_keys=True).encode()+sys.executable.encode()).hexdigest()


def run_checked(name,command,env,root,heartbeat=30):
    root=Path(root);logs=root/'supervision';logs.mkdir(exist_ok=True)
    proof=logs/(name+'-passed.json');key=fingerprint(root,env)
    # Only the synthetic admission may be reused. Never infer market completion
    # from a heartbeat, missing PID, stale local status or successful source setup.
    if name=='synthetic' and proof.exists() and json.loads(proof.read_text()).get('fingerprint')==key:
        print('REUSE synthetic: verified local admission under identical scope/environment',flush=True);return ''
    attempt=uuid.uuid4().hex[:12];status=logs/(name+'-'+attempt+'.json');logpath=logs/(name+'-'+attempt+'.log')
    state={'phase':name,'attempt':attempt,'started':stamp(),'status':'STARTING','exit_code':None,'log':str(logpath),'source':PIN}
    durable(status,state)
    env=dict(env);env['PYTHONUNBUFFERED']='1'
    token=env.get('GH_TOKEN','').encode();pending=b'';collected=[];saved=0
    def clean(data):return data.replace(token,b'[REDACTED]') if token else data
    with logpath.open('ab',buffering=0) as log:
        def emit(data):
            nonlocal saved
            if not data:return
            data=clean(data);log.write(data);os.fsync(log.fileno())
            print(data.decode('utf-8','replace'),end='',flush=True)
            # Limit returned text; full output stays in the append-only log.
            if saved<65536:collected.append(data[:65536-saved]);saved+=len(collected[-1])
        emit(('START '+name+' '+stamp()+'\n').encode())
        try:
            child=subprocess.Popen(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                bufsize=0,pass_fds=(() if LOCK_FD is None else (LOCK_FD,)))
            state.update(status='RUNNING',pid=child.pid,supervisor_pid=os.getpid());durable(status,state)
            sel=selectors.DefaultSelector();sel.register(child.stdout,selectors.EVENT_READ)
            last=time.monotonic()
            while sel.get_map():
                for event,_ in sel.select(timeout=min(1,heartbeat)):
                    data=os.read(event.fileobj.fileno(),4096)
                    if not data:sel.unregister(event.fileobj);break
                    pending+=data
                    cut=len(pending)
                    if token:
                        # Hold only a suffix that could be an incomplete secret,
                        # never the last N ordinary log bytes indiscriminately.
                        for length in range(min(len(token)-1,len(pending)),0,-1):
                            if pending.endswith(token[:length]):cut-=length;break
                    emit(pending[:cut]);pending=pending[cut:]
                if time.monotonic()-last>=heartbeat:
                    state['last_observed']=stamp();state['child_alive']=child.poll() is None;durable(status,state)
                    emit(('HEARTBEAT '+name+' child_alive='+str(state['child_alive'])+'; completion not established\n').encode());last=time.monotonic()
            emit(pending);code=child.wait();sel.close();child.stdout.close()
            state.update(status='PASSED' if code==0 else 'FAILED',exit_code=code,finished=stamp());durable(status,state)
            emit(('EXIT '+name+' '+str(code)+'\n').encode())
            if code:raise RuntimeError(name+' exit '+str(code)+'; durable log: '+str(logpath))
            durable(proof,{'fingerprint':key,'exit_code':0,'attempt':attempt,'finished':stamp()})
            return b''.join(collected).decode('utf-8','replace')
        except BaseException as exc:
            # SIGKILL cannot be caught. The already flushed RUNNING record then
            # remains an observation, never a claim of current process liveness.
            state.update(status='FAILED' if state.get('exit_code') is not None else 'INTERRUPTED',error=clean(str(exc).encode()).decode(),observed=stamp());durable(status,state)
            raise
