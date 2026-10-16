"""Run the official Graphify CLI on a pinned NOVA text/code corpus."""
from pathlib import Path
import subprocess,sys,os,json,time
ROOT=Path(__file__).resolve().parent
def main():
    audit=json.loads((ROOT/'SOURCE-AUDIT.json').read_text());assert audit['status']=='PASS'
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'runtime');env['XDG_CACHE_HOME']=str(ROOT/'cache');env['GRAPHIFY_QUERY_LOG_DISABLE']='1';env['GRAPHIFY_OUT']=str(ROOT/'graphify-out');env['PYTHONHASHSEED']='0'
    command=[sys.executable,'-m','graphify','extract',str(ROOT/'corpus'),'--code-only','--out',str(ROOT/'graphify-out')]
    started=time.monotonic()
    with (ROOT/'extract.log').open('w') as f:
        p=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT)
    report={'command':command,'exit_code':p.returncode,'seconds':time.monotonic()-started,'source_commit':audit['source_commit'],'input_files_verified':audit['verified_files'],'mode':'official Graphify local code-only extraction; no LLM backend; no source code execution','output_files':[{'path':str(x.relative_to(ROOT)),'bytes':x.stat().st_size} for x in (ROOT/'graphify-out').rglob('*') if x.is_file()]}
    (ROOT/'RUN.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
    raise SystemExit(p.returncode)
if __name__=='__main__':main()
