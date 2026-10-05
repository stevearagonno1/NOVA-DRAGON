"""Upload small R1 result/code buffers via GitHub Git database API only."""
from __future__ import annotations
import hashlib,os
from pathlib import Path
from .transport import GitHubTransport,TransportError

MAX_PART_BYTES=8_000_000


def publish_files(local_root:str,relative_paths:list[str],message:str,log_append:str,
                  tick_path:str,tick_text:str):
    root=Path(local_root).resolve();client=GitHubTransport();parent=client.branch_head()
    files={}
    for rel in relative_paths:
        p=Path(rel)
        if p.is_absolute() or '..' in p.parts:raise ValueError('unsafe relative path')
        full=(root/p).resolve()
        if root not in full.parents:raise ValueError('path escaped local root')
        data=full.read_bytes()
        if len(data)>MAX_PART_BYTES:raise TransportError(f'{rel}: buffer exceeds 8,000,000 byte partition cap')
        files[rel]=data
    old_log=client.blob_from_commit(parent,'LOG.md')
    files['LOG.md']=old_log+log_append.encode('utf-8')
    files[tick_path]=tick_text.encode('utf-8')
    commit,receipts=client.commit_files(files,parent,message)
    verified=[]
    for rel,data in files.items():
        remote=client.blob_from_commit(commit,rel)
        if hashlib.sha256(remote).digest()!=hashlib.sha256(data).digest() or len(remote)!=len(data):
            raise TransportError(f'{rel}: remote committed content mismatch')
        verified.append({'path':rel,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'git_blob_sha':next(r.blob_sha for r in receipts if r.path==rel),'commit_sha':commit})
    return {'parent':parent,'commit':commit,'branch_head':client.branch_head(),'files':verified}
