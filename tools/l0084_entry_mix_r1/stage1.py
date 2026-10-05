"""Stage 1 only: registered singleton measurements, no pair/triple selection.

Reuses the pinned R1 engine, panels, bounded writers and independent reference.
This stage supplies evidence for Lead review, not an adoption verdict.
"""
from __future__ import annotations
import argparse
import base64
from collections import OrderedDict
import hashlib
import json
import os
import time
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from . import measure as M, indicators as I, streaming as W, audit as A
from . import transport as T

BRANCH = 'agent/l0084-r1-stage1-2026-10-05'
RUN = 'stage1-singletons-v1'
BASE = W.BASE + '/stages/01-singletons'


class PacedTransport(T.GitHubTransport):
    """At most 240 writes/hour and 1800 total requests/hour per process.

Retries inside the parent request are bounded but may add one request.
Server Retry-After is still authoritative; another publisher must be stopped.
"""
    def __init__(self, *args, clock=time.monotonic, sleeper=time.sleep, **kw):
        super().__init__(*args, **kw)
        self.clock, self.sleeper = clock, sleeper
        self.last_request = self.last_write = None
        self.trees = OrderedDict()

    def _request(self, path, method='GET', payload=None):
        now = self.clock()
        wait = max(0.0, (self.last_request + 2 - now) if self.last_request is not None else 0.0,
                   (self.last_write + 15 - now) if method != 'GET' and self.last_write is not None else 0.0)
        if wait: self.sleeper(wait)
        self.last_request = self.clock()
        if method != 'GET': self.last_write = self.last_request
        return super()._request(path, method, payload)

    def _tree(self, commit):
        if commit not in self.trees:
            tree_sha = self._request('/git/commits/' + commit)[1]['tree']['sha']
            response = self._request('/git/trees/' + tree_sha + '?recursive=1')[1]
            if response.get('truncated'): raise T.TransportError('truncated tree; refusing incomplete evidence')
            self.trees[commit] = {r['path']:r for r in response['tree']}
            if len(self.trees) > 8: self.trees.popitem(last=False)
        self.trees.move_to_end(commit)
        return self.trees[commit]

    def blob_from_commit(self, commit_sha, path):
        row = self._tree(commit_sha).get(path)
        if row is None or row['type'] != 'blob': raise T.TransportError('path resolution failed: ' + path)
        obj = self._request('/git/blobs/' + row['sha'])[1]
        if obj.get('encoding') != 'base64': raise T.TransportError('unexpected blob encoding')
        data = base64.b64decode(obj['content'])
        if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() != row['sha']:
            raise T.TransportError('Git blob SHA mismatch')
        return data

    def list_directory(self, commit_sha, path):
        prefix = path.rstrip('/') + '/'
        names = sorted({p[len(prefix):].split('/')[0] for p in self._tree(commit_sha) if p.startswith(prefix)})
        if not names: raise T.TransportError('directory resolution failed: ' + path)
        return names


def measure_stage(m, writer, settings):
    """One fixed grid: each singleton and no-signal, every registered window."""
    for candidate in ['NO-SIGNAL', *settings]:
        for window, _, _ in M.HALF_YEARS:
            baseline = m.baseline(window)
            base_trades = (baseline or {}).get('per_asset', {s: [] for s in m.panels})
            trades = base_trades if candidate == 'NO-SIGNAL' else m.candidate_trades((candidate,), 'AND0', window=window)
            writer.add_window(candidate, 'baseline' if candidate == 'NO-SIGNAL' else 'single', window,
                              trades, m.panels, baseline_by_asset=base_trades,
                              members=None if candidate == 'NO-SIGNAL' else (candidate,), mode='AND0')
    return writer.close()


def audit_stage(client, head, run, m, settings):
    """Check every raw field against a separate portfolio/exit implementation."""
    coverage = A._run_index(client, head, run)
    wanted = {(c, 'baseline' if c == 'NO-SIGNAL' else 'single', w)
              for c in ['NO-SIGNAL', *settings] for w, _, _ in M.HALF_YEARS}
    found = {(x['candidate_id'], x['role'], x['window']) for x in coverage}
    if found != wanted or len(coverage) != len(wanted):
        raise T.TransportError('stage1 coverage missing, duplicated, or outside singleton scope')
    result = A.verify_remote_partitions(client, head, run)
    count = 0
    for group in coverage:
        candidate, role, window = group['candidate_id'], group['role'], group['window']
        actual = []
        for path in group['partition_paths']:
            actual.extend(pq.read_table(pa.BufferReader(client.blob_from_commit(head, path))).to_pylist())
        expected = []
        for symbol, panel in m.panels.items():
            lo, hi = panel.ranges[window]
            mask = None if role == 'baseline' else panel.mask_of(candidate)
            trades = A.independent_simulate_window(panel.o, panel.h, panel.l, panel.c, panel.atr,
                                                   panel.seg, mask, symbol, candidate, lo, hi)
            expected.extend(W._row(t, candidate, role, window, m.panels) for t in trades)
        key = lambda r: (r['asset'], r['signal_bar'], r['fill_bar'])
        actual.sort(key=key); expected.sort(key=key)
        if len(actual) != len(expected): raise T.TransportError('independent row count mismatch')
        for got, want in zip(actual, expected):
            for field in W.TRADE_SCHEMA.names:
                a, b = got[field], want[field]
                if isinstance(b, float):
                    ok = a is not None and np.isclose(a, b, rtol=1e-10, atol=1e-10, equal_nan=True)
                else: ok = a == b
                if not ok: raise T.TransportError('independent raw-field mismatch: ' + field)
        count += len(actual)
    return {'status': 'PASS', 'groups': len(coverage), 'trade_rows': count,
            'raw_partition_reconciliation': result, 'scope': 'singletons_and_no_signal_only',
            'strategy_adoption': 'NOT EVALUATED', 'metrics_and_inference_final_audit': 'Lead review pending'}


def synthetic_check():
    from .synthetic import SyntheticMeasurer, SyntheticPanel
    from .test_streaming import MemoryTransport
    from .data import ASSETS
    settings = list(I.SETTINGS_52); m = SyntheticMeasurer(settings); client = MemoryTransport()
    m.panels = {s: SyntheticPanel(s, settings) for s in ASSETS}
    writer = W.RemoteTradeWriter(client, run_id='stage1-synthetic', max_rows=5000)
    summary = measure_stage(m, writer, settings)
    first = audit_stage(client, client.branch_head(), 'stage1-synthetic', m, settings)
    # A complete rerun must recover the same rows without duplicated indices.
    writer = W.RemoteTradeWriter(client, run_id='stage1-synthetic', max_rows=5000)
    resumed = measure_stage(m, writer, settings)
    second = audit_stage(client, client.branch_head(), 'stage1-synthetic', m, settings)
    assert first['trade_rows'] == second['trade_rows'] == summary['rows'] == resumed['rows']
    # Interrupted upload leaves a recoverable partial run.
    broken = MemoryTransport(fail='blob_before_ref')
    try: measure_stage(m, W.RemoteTradeWriter(broken, run_id='stage1-interrupt', max_rows=5000), settings)
    except RuntimeError: pass
    else: raise AssertionError('interruption fixture did not interrupt')
    measure_stage(m, W.RemoteTradeWriter(broken, run_id='stage1-interrupt', max_rows=5000), settings)
    recovered = audit_stage(broken, broken.branch_head(), 'stage1-interrupt', m, settings)
    assert recovered['trade_rows'] == first['trade_rows']
    # Altering a remote raw partition must be rejected.
    index = A._run_index(client, client.branch_head(), 'stage1-synthetic')
    path = next(p for row in index for p in row['partition_paths'])
    client.trees[client.branch_head()][path] = b'tampered'
    try: audit_stage(client, client.branch_head(), 'stage1-synthetic', m, settings)
    except Exception: pass
    else: raise AssertionError('tampering was accepted')
    return {'status':'PASS', 'measurement_and_independent_raw_audit': first,
            'completed_resume':'PASS', 'interrupted_resume':'PASS', 'tampering':'REJECTED',
            'pairs_and_triples':'NOT RUN', 'market_outcomes_read':False}


def main(argv=None):
    parser = argparse.ArgumentParser(); parser.add_argument('--synthetic', action='store_true')
    parser.add_argument('--mode', choices=['measure','audit'], default='measure')
    args = parser.parse_args(argv)
    if args.synthetic:
        print(json.dumps(synthetic_check(), indent=2)); return 0
    T.BRANCH = BRANCH
    client = PacedTransport(); head = client.branch_head()
    # Scope and definition hashes are fixed before this run starts.
    scope = json.loads(client.blob_from_commit(head, BASE + '/scope.json'))
    if scope['settings'] != list(I.SETTINGS_52) or scope['windows'] != [w[0] for w in M.HALF_YEARS]:
        raise T.TransportError('stage1 preregistered grid mismatch')
    for name, digest in scope['code_sha256'].items():
        local = Path(__file__).parent / name
        if hashlib.sha256(local.read_bytes()).hexdigest() != digest:
            raise T.TransportError('stage1 pinned code hash mismatch: ' + name)
    # Existing raw panels are read one at a time into memory; no second local copy.
    from . import data as D
    sources = {r['asset']:r for r in scope['input_panels']}
    if set(sources) != set(D.ASSETS): raise T.TransportError('stage1 asset universe mismatch')
    original_loader = D.load_asset
    def verified_loader(work, symbol):
        row = sources[symbol]
        data = client.blob_from_commit(head, row['path'])
        T.verify_bytes(data, row['sha256'], row['bytes'])
        return pq.read_table(pa.BufferReader(data)).to_pandas()
    D.load_asset = verified_loader
    try: m = M.Measurer()
    finally: D.load_asset = original_loader
    if args.mode == 'measure':
        writer = W.RemoteTradeWriter(client, run_id=RUN, max_rows=5000)
        summary = measure_stage(m, writer, scope['settings'])
        payload = {'status':'RAW_MEASUREMENT_COMPLETE_AUDIT_PENDING', 'run_id':RUN,
                   'scope':scope, 'writer':summary, 'no_pairs_or_triples':True}
        new, _ = client.commit_files({BASE+'/measurement.json':json.dumps(payload,indent=2).encode()},
                                     client.branch_head(), 'L0084 stage 1: singleton raw measurement complete')
        print(json.dumps({'status':payload['status'], 'head':new, 'run_id':RUN})); return 0
    result = audit_stage(client, head, RUN, m, scope['settings'])
    result['fixed_head'] = head
    new, _ = client.commit_files({BASE+'/raw_audit.json':json.dumps(result,indent=2).encode()},
                                 client.branch_head(), 'L0084 stage 1: complete independent raw audit')
    print(json.dumps({'status':'RAW_AUDIT_PASS_LEAD_REVIEW_PENDING', 'head':new})); return 0


if __name__ == '__main__': raise SystemExit(main())
