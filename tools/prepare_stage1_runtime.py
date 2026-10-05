"""Prepared dependency setup; no research-code or market-data modification."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

VERSIONS = {'numpy': ['2.3.5'], 'pandas': ['2.2.3'],
            'scipy': ['1.17.0', '1.17.1'], 'pyarrow': ['25.0.1']}
PROBE = r'''
import json, importlib
allowed = %s
versions = {}; issues = {}
for name, accepted in allowed.items():
    try:
        m = importlib.import_module(name); versions[name] = m.__version__
        if m.__version__ not in accepted: issues[name] = 'version: '+m.__version__
    except Exception as e: issues[name] = type(e).__name__+': '+str(e)
if not issues:
    try:
        import pyarrow as pa, pyarrow.parquet as pq
        table = pa.table({'asset':['fixture','fixture'], 'gross':[1.0,-0.3], 'cost':[0.052,0.052]})
        sink = pa.BufferOutputStream(); pq.write_table(table,sink,compression='zstd',version='2.6')
        if not pq.read_table(pa.BufferReader(sink.getvalue())).equals(table):
            raise RuntimeError('Parquet round-trip mismatch')
    except Exception as e: issues['pyarrow'] = type(e).__name__+': '+str(e)
print(json.dumps({'versions':versions,'issues':issues,'parquet_roundtrip':'PASS' if not issues else 'NOT RUN'}))
''' % repr(VERSIONS)


def prepare(target, workspace, runner=subprocess.run):
    target=Path(target).resolve(); workspace=Path(workspace).resolve()
    if target == workspace or workspace in target.parents:
        raise RuntimeError('dependency directory must be outside the experiment workspace')
    target.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ); env.pop('GH_TOKEN',None)
    env['PYTHONPATH']=str(target)+os.pathsep+env.get('PYTHONPATH','')
    env['PYTHONDONTWRITEBYTECODE']='1'
    temporary=target/'installer-temporary';temporary.mkdir(exist_ok=True)
    env['TMPDIR']=str(temporary)
    def probe():
        result=runner([sys.executable,'-c',PROBE],env=env,text=True,capture_output=True)
        if result.returncode:
            raise RuntimeError('dependency probe exit '+str(result.returncode)+': '+result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])
    before=probe()
    if before['issues']:
        requirements=(['pyarrow==25.0.1'] if set(before['issues'])=={'pyarrow'}
                      else ['numpy==2.3.5','pandas==2.2.3','scipy==1.17.1','pyarrow==25.0.1'])
        command=[sys.executable,'-m','pip','install','--index-url','https://pypi.org/simple',
                 '--target',str(target),'--upgrade','--only-binary=:all:',
                 '--no-cache-dir','--disable-pip-version-check']
        if requirements==['pyarrow==25.0.1']:command.append('--no-deps')
        result=runner(command+requirements,env=env,text=True,capture_output=True)
        if result.returncode:
            raise RuntimeError('prepared dependency install exit '+str(result.returncode)+': '+result.stdout+'\n'+result.stderr)
    after=probe()
    if after['issues']:raise RuntimeError('dependency setup incomplete: '+json.dumps(after['issues']))
    return {'status':'PASS','external_runtime':str(target),'python':sys.version.split()[0],
            **after,'initial_issues':before['issues'],'market_outcomes_read':False}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--target',default='/tmp/nova-stage1-runtime-'+sys.implementation.cache_tag)
    parser.add_argument('--workspace',default='/home/user')
    args=parser.parse_args();print(json.dumps(prepare(args.target,args.workspace),indent=2))


if __name__=='__main__':main()
