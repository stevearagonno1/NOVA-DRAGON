from pathlib import Path
import json,urllib.request,urllib.parse,hashlib,concurrent.futures,subprocess,zipfile,xml.etree.ElementTree as ET
P=Path(__file__).resolve().parent
M=json.loads((P/'binary-document-inventory.json').read_text()); D=P/'document_evidence';D.mkdir(exist_ok=True)
def run(pair):
 i,f=pair; suffix=Path(f['path']).suffix; dest=D/(f'{i:02d}'+suffix)
 try:
  url='https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/'+M['source_commit']+'/'+urllib.parse.quote(f['path'],safe='/')
  b=urllib.request.urlopen(url,timeout=90).read()
  assert len(b)==f['bytes'] and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==f['git_sha']
  dest.write_bytes(b); out=dest.with_suffix('.txt')
  if suffix=='.pdf':
   p=subprocess.run(['pdftotext','-layout',str(dest),str(out)],capture_output=True);assert p.returncode==0,p.stderr.decode(errors='replace')
  else:
   with zipfile.ZipFile(dest) as z: root=ET.fromstring(z.read('word/document.xml'))
   ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
   out.write_text('\n'.join(''.join(n.itertext()) for p in root.findall('.//w:p',ns) for n in [ET.Element('dummy')]) if False else '\n'.join(''.join(n.text or '' for n in p.findall('.//w:t',ns)) for p in root.findall('.//w:p',ns)))
  t=out.read_text();return dict(f,index=i,status='TEXT_EXTRACTED_NOT_SEMANTICALLY_REVIEWED',characters=len(t),text_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),text_path=str(out.relative_to(P)))
 except Exception as e:return dict(f,index=i,status='EXTRACTION_FAILED',reason=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: results=list(pool.map(run,enumerate(M['files'],1)))
(P/'document-extraction.json').write_text(json.dumps({'source_commit':M['source_commit'],'files':results},ensure_ascii=False,indent=2))
print(json.dumps({'files':len(results),'extracted':sum(x['status'].startswith('TEXT_') for x in results),'characters':sum(x.get('characters',0) for x in results),'failed':[x for x in results if x['status']=='EXTRACTION_FAILED']},ensure_ascii=False))
