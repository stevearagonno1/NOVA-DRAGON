"""Read the pinned owner archive in memory; never execute its definitions.

This is an inventory/admission audit, NOT a market backtest or a readiness gate.
All source rows survive, including non-bullish and unresolved records.
"""
import argparse
import ast
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import zipfile

ARCHIVE_SHA = 'd536b7d84ea94f93f080d81086b3ffbe3f2803a8d413fabaaf268c0f7cd1298a'
DB_SHA = '19d730d9d4b7f537d0591a55786370331712c9aacb520229714e2cc9f7c60cfc'
TABLES = ('versions', 'volume_versions', 'source_condition_candidates',
          'web_standalone_records', 'bullish_candidates_pending_review')

def encoded(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def unresolved(value):
    if isinstance(value, dict):
        return bool(value.get('unresolved')) or 'expression' in value or any(unresolved(v) for v in value.values())
    if isinstance(value, list):
        return any(unresolved(v) for v in value)
    return False

def definition_flags(body):
    flags = set()
    code = body.get('definition', '')
    if not isinstance(code, str):
        return ['definition_not_text']
    if body.get('scope') == 'dust_sweep_if_due':
        flags.add('administrative_dust_conversion')
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return sorted(flags | {'non_python_or_unparsed_definition'})
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    if names & {'REST', 'requests', 'subprocess', 'os'}:
        flags.add('external_side_effect')
    if names & {'CANDLES', 'STATE', 'STATE_LOCK', 'live_execution_allowed'}:
        flags.add('live_state_dependency')
    return sorted(flags)

def classify_bull(row, versions, definitions, grid, flags):
    blockers = {'bullish_adapter_not_validated'}
    bindings = []
    fields = ('id', 'family', 'definition_id', 'settings', 'asset', 'origin', 'signal', 'timing')
    ids = row.get('source_version_ids', [])
    if not ids:
        blockers.add('missing_source_version')
    for ident in ids:
        source = versions.get(ident)
        if source is None:
            blockers.add('missing_source_version')
            continue
        did = source.get('definition_id')
        if did not in definitions:
            blockers.add('missing_definition')
        else:
            blockers.update(flags.get(did, definition_flags(definitions[did])))
        old = grid.get(ident)
        if old and all(source.get(k) == old.get(k) for k in fields):
            bindings.append(ident)
        if unresolved(source.get('settings', {})):
            blockers.add('unresolved_source_settings')
    if not bindings:
        blockers.add('no_existing_exact_source_binding')
    if unresolved(row.get('settings', {})) or row.get('unresolved_parameters'):
        blockers.add('unresolved_candidate_settings')
    if row.get('confirmation', 'NONE') != 'NONE' or row.get('timing', 'NOW') != 'NOW':
        blockers.add('confirmation_or_sequence_not_validated')
    return {'id': row['id'], 'market_ready': False,
            'existing_source_bindings': sorted(bindings), 'blockers': sorted(blockers)}

def disk_size(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())

def write_rows(path, rows, workspace):
    """Deterministic gzip, with whole-workspace budget checked before each write."""
    baseline = disk_size(workspace)
    with path.open('xb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as out:
            for row in rows:
                data = encoded(row) + b'\n'
                # This command is the sole workspace writer. Include all other
                # files, bytes written here, and gzip's pending buffer allowance.
                if baseline + raw.tell() + len(data) + 65536 > 125_000_000:
                    raise RuntimeError('125 MB whole-workspace limit')
                out.write(data)
    return {'bytes': path.stat().st_size, 'sha256': digest(path.read_bytes())}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', required=True, type=Path)
    p.add_argument('--grid', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--workspace', required=True, type=Path,
                   help='Actual entire task workspace, never a smaller budget bypass directory')
    a = p.parse_args()
    root = a.workspace.resolve()
    for item in (a.archive, a.grid, a.output):
        if not item.resolve().is_relative_to(root):
            raise ValueError('All task files must be within whole workspace')
    if disk_size(root) >= 125_000_000:
        raise RuntimeError('125 MB whole-workspace limit')
    if digest(a.archive.read_bytes()) != ARCHIVE_SHA:
        raise ValueError('Archive bytes changed')
    with zipfile.ZipFile(a.archive) as z:
        data = z.read('NOVA-separated.sqlite')
    if digest(data) != DB_SHA:
        raise ValueError('Database bytes changed')
    db = sqlite3.connect(':memory:')
    db.deserialize(data)
    del data
    db.row_factory = sqlite3.Row
    db.executescript('PRAGMA query_only=ON; PRAGMA trusted_schema=OFF; PRAGMA temp_store=MEMORY;')
    if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
        raise ValueError('SQLite integrity check failed')
    versions = {r['id']: dict(r) for r in db.execute('SELECT * FROM versions')}
    for r in versions.values():
        r['settings'] = json.loads(r['settings'])
    definitions = {r['id']: json.loads(r['body']) for r in db.execute('SELECT * FROM definitions')}
    flags = {k: definition_flags(v) for k, v in definitions.items()}
    grid = {r['id']: r for r in json.loads(a.grid.read_text())}
    a.output.mkdir(parents=True, exist_ok=False)
    files, counts, families, reasons, claimed, bound = {}, {}, Counter(), Counter(), Counter(), 0
    def candidates():
        nonlocal bound
        for raw in db.execute('SELECT * FROM bullish_candidates_pending_review ORDER BY id'):
            row = json.loads(raw['body'])
            audit = classify_bull(row, versions, definitions, grid, flags)
            audit['source_row_sha256'] = digest(encoded(dict(raw)))
            families[row['family']] += 1
            reasons.update(audit['blockers'])
            claimed[row.get('readiness', 'unspecified')] += 1
            bound += bool(audit['existing_source_bindings'])
            yield {'candidate': row, 'audit': audit}
    files['bullish-candidates.jsonl.gz'] = write_rows(a.output/'bullish-candidates.jsonl.gz', candidates(), root)
    # Preserve every original physical row; direction is not inferred from names.
    def sources():
        for table in TABLES:
            n = 0
            for r in db.execute('SELECT * FROM '+table+' ORDER BY id'):
                obj = dict(r)
                yield {'table': table, 'source_row_sha256': digest(encoded(obj)), 'record': obj}
                n += 1
            counts[table] = n
    files['source-ledger.jsonl.gz'] = write_rows(a.output/'source-ledger.jsonl.gz', sources(), root)
    def recipes():
        for table in ('parameter_axes', 'axis_values', 'volume_spaces', 'definitions', 'sources', 'web_sources'):
            for r in db.execute('SELECT * FROM '+table+' ORDER BY 1,2'):
                yield {'table': table, 'record': dict(r)}
        for r in db.execute("SELECT name,sql FROM sqlite_master WHERE type='view' ORDER BY name"):
            yield {'table': 'view_recipes', 'record': dict(r)}
    files['recipes-and-definitions.jsonl.gz'] = write_rows(a.output/'recipes-and-definitions.jsonl.gz', recipes(), root)
    # Direct count is independent of stale summary metadata. No 17M-row export.
    variant_count = db.execute('SELECT COUNT(*) FROM individual_parameter_variants').fetchone()[0]
    report = {'schema': 1, 'archive_sha256': ARCHIVE_SHA, 'database_sha256': DB_SHA,
              'grid_sha256': digest(a.grid.read_bytes()), 'counts': counts,
              'single_parameter_variants': variant_count,
              'independent_catalog_including_bases': variant_count+len(versions),
              'bullish_families': len(families), 'families': dict(sorted(families.items())),
              'blocker_counts': dict(sorted(reasons.items())), 'source_claimed_readiness': dict(claimed),
              'candidates_with_existing_base_binding': bound,
              'market_tests_executed': 0, 'new_bullish_adapters_validated': 0,
              'all_source_rows_preserved': sum(counts.values()), 'files': files,
              'limits': ['Static flags are conservative, not a security proof.',
                         'Base binding does not validate a derived bullish rule.',
                         'No new combinations or market accuracy results in this inventory.',
                         'All other physical records retained for directional review.']}
    (a.output/'summary.json').write_bytes(encoded(report)+b'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='families'}, ensure_ascii=False))
    db.close()

if __name__ == '__main__':
    main()
