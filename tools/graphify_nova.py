"""Repository CLI integration. Run after installing requirements-graphify.lock.txt."""
from pathlib import Path
import argparse,subprocess,sys,os
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--output',default='graphify-out');p.add_argument('--query');a=p.parse_args()
    env=os.environ.copy();env['GRAPHIFY_QUERY_LOG_DISABLE']='1';env['GRAPHIFY_OUT']=str(Path(a.output).resolve())
    if a.query:cmd=[sys.executable,'-m','graphify','query',a.query]
    else:cmd=[sys.executable,'-m','graphify','extract',str(Path(a.root).resolve()),'--code-only','--out',env['GRAPHIFY_OUT']]
    raise SystemExit(subprocess.call(cmd,env=env))
if __name__=='__main__':main()
