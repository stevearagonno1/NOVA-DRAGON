"""Verify owner catalog without executing any indicator source code."""
import argparse,zipfile,json,hashlib,sqlite3
p=argparse.ArgumentParser();p.add_argument('archive');a=p.parse_args()
with zipfile.ZipFile(a.archive) as z:
    manifest=json.loads(z.read('SHA256.json'))
    for n,h in manifest.items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
    c=sqlite3.connect(':memory:');c.deserialize(z.read('NOVA-separated.sqlite'))
    assert c.execute('pragma quick_check').fetchone()[0]=='ok'
    tables=['versions','volume_versions','parameter_axes','definitions','sources','source_condition_candidates','web_standalone_records','bullish_candidates_pending_review','individual_parameter_variants']
    counts={t:c.execute('select count(*) from '+t).fetchone()[0] for t in tables}
    counts['independent_indicator_catalog']=counts['versions']+counts['individual_parameter_variants']
    original=json.loads(z.read('summary.json'))
    print(json.dumps({'hashes_checked':len(manifest),'counts':counts,'original_summary':original,'summary_discrepancy':counts['individual_parameter_variants']-original['indexed_single_changes'],'market_accuracy':'not measured'},ensure_ascii=False,indent=2))
