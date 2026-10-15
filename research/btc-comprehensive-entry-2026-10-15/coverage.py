"""Recompute coverage counts and enumerate the proposed causal context dictionary.
This validates the inventory; it is not a market experiment or Pine interpreter.
"""
import argparse,gzip,hashlib,itertools,json,re,urllib.parse,urllib.request
from pathlib import Path
P=Path(__file__).resolve().parent
def load():
    raw=P/'inventory.json'
    if raw.exists():return json.loads(raw.read_text())
    return json.loads(gzip.decompress((P/'inventory.json.gz').read_bytes()))
def declarations(s):
    chars=list(s);quote=None;escape=False;line=False;block=False;i=0
    while i<len(s):
        c=s[i];n=s[i+1] if i+1<len(s) else ''
        if line:
            if c=='\n':line=False
            else:chars[i]=' '
        elif block:
            if c=='*' and n=='/':chars[i]=chars[i+1]=' ';i+=1;block=False
            elif c!='\n':chars[i]=' '
        elif quote:
            if c!='\n':chars[i]=' '
            if escape:escape=False
            elif c=='\\':escape=True
            elif c==quote:quote=None
        elif c=='/' and n in ('/','*'):
            chars[i]=chars[i+1]=' ';i+=1
            if n=='/':line=True
            else:block=True
        elif c in ('"',"'"):quote=c;chars[i]=' '
        i+=1
    mask=''.join(chars);pattern=r'\binput(?:\.(?:int|float|bool|string|source|timeframe|session|color|symbol|text_area|price|time|enum))?\s*\('
    output=[];position=0
    while True:
        m=re.search(pattern,mask[position:])
        if not m:break
        begin=position+m.start();opening=position+m.end()-1;j=opening+1;depth=1
        while j<len(mask) and depth:
            if mask[j]=='(':depth+=1
            elif mask[j]==')':depth-=1
            j+=1
        assert not depth,'Unbalanced declaration'
        output.append((s.count('\n',0,begin)+1,s[begin:j]));position=j
    return output
def main(verify):
    inv=load();assert not inv['errors'] and inv['read_files']==inv['expected_files']==len(inv['files'])
    assert len({x['path'] for x in inv['files']})==len(inv['files'])
    for f in inv['files']:assert f['git_sha']==f['returned_git_sha']
    counts={'files':len(inv['files']),'source_scripts':sum(f['kind']=='source_script' for f in inv['files']),'research_notes':sum(f['kind']=='research_notes' for f in inv['files']),'input_declarations':sum(len(f['inputs']) for f in inv['files'])}
    for status in ['EXPLICIT_FINITE_OPTIONS','DEFAULT_ONLY_RANGE_NOT_ENUMERATED','SYMBOLIC_DEFAULT_OR_DOMAIN_REQUIRES_REVIEW']:
        counts[status]=sum(x.get('domain_status')==status for f in inv['files'] for x in f['inputs'])
    assert sum(counts[s] for s in ['EXPLICIT_FINITE_OPTIONS','DEFAULT_ONLY_RANGE_NOT_ENUMERATED','SYMBOLIC_DEFAULT_OR_DOMAIN_REQUIRES_REVIEW'])==counts['input_declarations']
    states=[{'state_id':i,'signs':list(v)} for i,v in enumerate(itertools.product([-1,0,1],repeat=6))]
    assert len(states)==729 and len({tuple(s['signs']) for s in states})==729
    (P/'state-dictionary-v1.json').write_text(json.dumps({'status':'PROPOSED_NOT_MARKET_VALIDATED','axes':['price_minus_ema20','ema20_change5','macd_histogram','rsi14_change5','atr14_relative_change5','volume_over_previous60_minus1'],'frame_minutes':[1,5,15,60],'state_count_per_frame':729,'state_frame_cells':2916,'states':states},indent=2)+'\n')
    counts['proposed_states_per_frame']=len(states);counts['proposed_state_frame_cells']=len(states)*4
    if verify:
        for f in inv['files']:
            url='https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/'+inv['source_commit']+'/'+urllib.parse.quote(f['path'],safe='/')
            with urllib.request.urlopen(url,timeout=45) as r:b=r.read()
            assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==f['git_sha']
            actual=declarations(b.decode('utf-8'))
            expected=[(x['line'],x['source_declaration']) for x in f['inputs']]
            assert actual==expected,f['path']
    (P/'coverage-check.json').write_text(json.dumps({'status':'PASS_INVENTORY_ACCOUNTING_ONLY','counts':counts,'raw_sources_refetched_in_this_command':verify,'market_run':False,'universal_engine_ready':False},indent=2)+'\n')
    print(json.dumps(counts))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify-sources',action='store_true');main(p.parse_args().verify_sources)
