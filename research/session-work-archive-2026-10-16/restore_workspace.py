"""Validate and restore split ZIP plus deduplicated paths into a new directory."""
import argparse,io,json,hashlib,zipfile,bisect,shutil
from pathlib import Path
class Joined(io.RawIOBase):
    def __init__(self,paths):
        self.paths=paths;self.ends=[];total=0
        for p in paths:total+=p.stat().st_size;self.ends.append(total)
        self.pos=0;self.size=total
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        n=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
        if n<0:raise ValueError('negative seek')
        self.pos=n;return n
    def read(self,n=-1):
        if n<0:n=self.size-self.pos
        chunks=[]
        while n>0 and self.pos<self.size:
            idx=bisect.bisect_right(self.ends,self.pos);start=0 if idx==0 else self.ends[idx-1]
            with self.paths[idx].open('rb') as f:
                f.seek(self.pos-start);b=f.read(min(n,self.ends[idx]-self.pos))
            chunks.append(b);self.pos+=len(b);n-=len(b)
        return b''.join(chunks)
def main():
    p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('--output');p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    source=Path(a.manifest).resolve();d=json.loads(source.read_text());parts=[]
    for item in d['parts']:
        f=source.parent/item['name'];assert f.stat().st_size==item['bytes'];assert hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256'];parts.append(f)
    published={x['workspace_path']:x for x in d['entries'] if x['status']=='included'}
    out=None
    if not a.verify_only:
        if not a.output:p.error('--output required unless --verify-only')
        out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
    def target(name):
        q=(out/name).resolve()
        if not q.is_relative_to(out):raise ValueError('unsafe archive path')
        return q
    with zipfile.ZipFile(Joined(parts)) as z:
        assert set(z.namelist())==set(published)
        for n in z.namelist():
            b=z.read(n);assert hashlib.sha256(b).hexdigest()==published[n]['published_sha256'],n
            if out:
                q=target(n);q.parent.mkdir(parents=True,exist_ok=True)
                with q.open('xb') as w:w.write(b)
    if out:
        for item in d['entries']:
            if item['status']=='duplicate_content':
                q=target(item['workspace_path']);src=target(item['restore_from']);q.parent.mkdir(parents=True,exist_ok=True)
                with q.open('xb') as w,src.open('rb') as r:shutil.copyfileobj(r,w)
    print(json.dumps({'status':'PASS','parts':len(parts),'unique_files':len(published),'duplicate_paths':d['duplicate_paths'],'all_archive_bytes_verified':True,'restored':out is not None}))
if __name__=='__main__':main()
