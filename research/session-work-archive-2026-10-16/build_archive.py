from pathlib import Path
import zipfile,json,hashlib,sqlite3,re,io,gzip,datetime

ROOT=Path(__file__).resolve().parent.parent
OUT=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
PAT=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')
roots=['repo_registration','publish_resume','registration_lead_review','causal_features_prep','causal_year_review','entry_signal_prep','btc_comprehensive_prep']
manifest=[];redactions=[];seen={};files=[]
def safe_bytes(b,name,depth=0):
    if depth>8:raise RuntimeError('Nested archive too deep: '+name)
    if b[:4]==b'PK\x03\x04':
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            changed=False;items=[]
            for i in z.infolist():
                data=z.read(i);new=safe_bytes(data,name+'!'+i.filename,depth+1);changed|=new!=data;items.append((i,new))
            if changed:
                out=io.BytesIO()
                with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as w:
                    for i,data in items:w.writestr(i,data)
                return out.getvalue()
    elif b[:2]==b'\x1f\x8b':
        raw=gzip.decompress(b);new=safe_bytes(raw,name+'!gzip',depth+1)
        if raw!=new:return gzip.compress(new,mtime=0)
    if PAT.search(b):
        redactions.append({'path':name,'matches':len(PAT.findall(b))})
        b=PAT.sub(b'[REDACTED_CREDENTIAL]',b)
    return b

class Parts:
    def __init__(self):self.pos=0;self.part=None;self.names=[];self.used=0
    def write(self,b):
        size=len(b)
        while b:
            if self.part is None or self.used==20_000_000:
                if self.part:self.part.close()
                p=OUT/('WORKSPACE-v2.zip.part%03d'%(len(self.names)+1));self.names.append(p);self.part=p.open('wb');self.used=0
            n=min(len(b),20_000_000-self.used);self.part.write(b[:n]);self.used+=n;self.pos+=n;b=b[n:]
        return size
    def tell(self):return self.pos
    def flush(self):
        if self.part:self.part.flush()
    def close(self):
        if self.part:self.part.close()

owner=ROOT/'upload/NOVA-all-originals-and-independent-versions (1).zip'
raw=owner.read_bytes();assert safe_bytes(raw,owner.name)==raw,'Owner archive must stay byte-identical'
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    hashes=json.loads(z.read('SHA256.json'))
    assert all(sha(z.read(n))==h for n,h in hashes.items())
    c=sqlite3.connect(':memory:');c.deserialize(z.read('NOVA-separated.sqlite'))
    assert c.execute('pragma quick_check').fetchone()[0]=='ok'
    counts={t:c.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ['versions','volume_versions','parameter_axes','definitions','sources','source_condition_candidates','web_standalone_records','bullish_candidates_pending_review','individual_parameter_variants']}
    counts['independent_indicator_catalog']=counts['versions']+counts['individual_parameter_variants']
    audit={'status':'TECHNICALLY_CONFIRMED_CATALOG_COUNTS_NOT_MARKET_VALIDATION','archive_sha256':sha(raw),'archive_bytes':len(raw),'manifest_hashes_checked':len(hashes),'sqlite_quick_check':'ok','counts':counts,'original_summary':json.loads(z.read('summary.json')),'summary_discrepancy':counts['individual_parameter_variants']-json.loads(z.read('summary.json'))['indexed_single_changes'],'all_variants_market_tested':False,'all_variants_executable_or_bullish':False}
    for n in ['README_AR.md','summary.json','original-index_AR.md','generate-independent.py','volume-generate.py','research/parameter-values.json','research/catalog_AR.md','research/sources.json','research/standalone-presets.json','research/video-candidates.json','research/allowed-ranges-not-used-values.json','SHA256.json']:
        p=OUT/'original-catalog'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
(OUT/'CATALOG-AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
for root in roots:
    for p in sorted((ROOT/root).rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(ROOT).as_posix()
        if any(x in p.parts for x in ['node_modules','__pycache__','.git']):continue
        if p.suffix in ['.pyc','.pyo']:continue
        if 'PRIVATE' in p.name.upper():
            manifest.append({'workspace_path':rel,'status':'excluded_private_credential_paper','public_equivalent':'Redacted/public papers retained where present'});continue
        b=p.read_bytes();s=sha(b)
        if b[:4]==b'PK\x03\x04' and not zipfile.is_zipfile(io.BytesIO(b)):
            manifest.append({'workspace_path':rel,'status':'excluded_damaged_archive_not_safely_inspectable','original_sha256':s,'bytes':len(b),'reason':'BadZipFile; preserved locally; verified frozen replacement retained separately where present'});continue
        if s in seen:
            manifest.append({'workspace_path':rel,'status':'duplicate_content','restore_from':seen[s],'original_sha256':s,'bytes':len(b)});continue
        seen[s]=rel;files.append((p,rel,s))
        manifest.append({'workspace_path':rel,'status':'included','original_sha256':s,'bytes':len(b)})
writer=Parts()
with zipfile.ZipFile(writer,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    bypath={x['workspace_path']:x for x in manifest}
    for p,rel,s in files:
        data=safe_bytes(p.read_bytes(),rel);bypath[rel]['published_sha256']=sha(data);bypath[rel]['credential_redacted']=data!=p.read_bytes()
        z.writestr(rel,data)
writer.close()
parts=[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in writer.names]
result={'snapshot_roots':roots,'entries':manifest,'unique_files_in_archive':len(files),'duplicate_paths':sum(x['status']=='duplicate_content' for x in manifest),'excluded_private_papers':sum(x['status']=='excluded_private_credential_paper' for x in manifest),'excluded_runtime_dependencies':['node_modules','__pycache__','*.pyc','*.pyo'],'credential_redactions':redactions,'parts':parts,'zip_reassembly':'Concatenate parts in listed order, then open the resulting ZIP. Duplicate paths map to restore_from. Original private credential papers are not uploaded.','owner_archive_is_separate_and_byte_identical':True,'all_market_measurements_or_universal_readiness_claimed':False}
(OUT/'WORKSPACE-MANIFEST.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'catalog_counts':counts,'snapshot_files':len(files),'duplicate_paths':result['duplicate_paths'],'private_papers_excluded':result['excluded_private_papers'],'redacted_locations':len(redactions),'parts':parts},ensure_ascii=False),flush=True)
