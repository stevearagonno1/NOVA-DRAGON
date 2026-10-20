"""Full-stream singleton discovery. Future labels never enter indicator masks.

Preparation runner; not an executor delivery package or an adoption engine.
"""
import argparse
import fcntl
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'btc_state_specialist'))
import specialist as S
from workspace_guard import preflight

ROOT = Path(__file__).resolve().parent


def singletons():
    return [q for q in S.grid() if not (
        q['origin'] == 'registered_L0092_setting'
        and q['settings']['mode'] != 'STANDALONE')]


def evaluate(close, masks, eligible, horizon, gain):
    c = np.asarray(close, dtype=float)
    e = np.asarray(eligible)
    if (c.ndim != 1 or len(c) == 0 or not np.isfinite(c).all() or (c <= 0).any()
            or type(horizon) is not int or horizon < 1
            or not np.isfinite(gain) or gain <= 0
            or e.dtype != bool or e.shape != c.shape):
        raise ValueError('invalid prices, eligibility, horizon or rise threshold')
    n = len(c)
    complete = np.arange(n) + horizon < n
    success = np.zeros(n, bool)
    first_hit = np.full(n, -1, int)
    for lag in range(1, min(horizon, n-1) + 1):
        hit = c[lag:] >= c[:-lag] * (1 + gain)
        fresh = hit & ~success[:-lag]
        first_hit[:n-lag][fresh] = lag
        success[:-lag] |= hit
    judged = e & complete
    opportunities = S.runs(success & judged, ['continuous'] * n)
    rows = []
    evidence = {}
    for ident, values in masks.items():
        a = np.asarray(values)
        if a.dtype != bool or a.shape != c.shape:
            raise ValueError('signal must be a boolean vector aligned with prices')
        a = a & e
        scored = a & complete
        tp = int((scored & success).sum())
        fp = int((scored & ~success).sum())
        counts = [int(a[start:end+1].sum()) for start, end in opportunities]
        delays = [int(np.flatnonzero(a[start:end+1])[0]) for start, end in opportunities if a[start:end+1].any()]
        rows.append(dict(candidate_id=ident, alerts=int(a.sum()), true_alerts=tp,
                         false_alerts=fp, unresolved_alerts=int((a & ~complete).sum()),
                         precision=tp/(tp+fp) if tp+fp else None,
                         precision_wilson95_descriptive=S.wilson(tp, tp+fp),
                         opportunities=len(opportunities), caught_opportunities=sum(x > 0 for x in counts),
                         opportunity_coverage=sum(x > 0 for x in counts)/len(counts) if counts else None,
                         repeated_true_alerts=sum(max(0, x-1) for x in counts),
                         median_delay_bars=float(np.median(delays)) if delays else None,
                         median_target_wait_bars=float(np.median(first_hit[scored & success])) if tp else None))
        evidence[ident] = S.pack(a)
    raw = dict(close=c.tolist(), eligible=S.pack(e), horizon=horizon, gain=gain,
               alerts=evidence, evaluation='forward-close-target; complete horizons only')
    return raw, rows


def audit(raw, rows):
    """Scalar re-derivation from prices and packed alerts, not evaluate()."""
    c = raw['close']; n = len(c); h = raw['horizon']; gain = raw['gain']
    eligible = int(raw['eligible'], 16)
    seen = set()
    positive = [False] * n
    for i in range(n-h):
        positive[i] = bool((eligible >> i) & 1) and any(c[j] >= c[i]*(1+gain) for j in range(i+1, i+h+1))
    groups = []; start = None
    for i in range(n+1):
        yes = i < n and positive[i]
        if yes and start is None: start = i
        if not yes and start is not None: groups.append((start, i)); start = None
    for row in rows:
        ident = row['candidate_id']; assert ident not in seen; seen.add(ident)
        bits = int(raw['alerts'][ident], 16)
        assert bits >= 0 and bits >> n == 0 and bits & ~eligible == 0
        tp = fp = unresolved = 0; waits = []
        for i in range(n):
            if not ((bits >> i) & 1): continue
            if i+h >= n: unresolved += 1; continue
            hits = [j-i for j in range(i+1, i+h+1) if c[j] >= c[i]*(1+gain)]
            if hits: tp += 1; waits.append(hits[0])
            else: fp += 1
        delays = []; repeated = 0
        for start, end in groups:
            indices = [i for i in range(start, end) if (bits >> i) & 1]
            if indices: delays.append(indices[0]-start); repeated += len(indices)-1
        expected = dict(alerts=tp+fp+unresolved, true_alerts=tp, false_alerts=fp,
                        unresolved_alerts=unresolved, precision=tp/(tp+fp) if tp+fp else None,
                        opportunities=len(groups), caught_opportunities=len(delays),
                        opportunity_coverage=len(delays)/len(groups) if groups else None,
                        repeated_true_alerts=repeated,
                        median_delay_bars=float(np.median(delays)) if delays else None,
                        median_target_wait_bars=float(np.median(waits)) if waits else None)
        for key, value in expected.items(): assert row[key] == value, (ident, key)
    assert seen == set(raw['alerts'])
    return len(rows)


def run(out, fixture=False, stop_after=None):
    preflight(target=out)
    cfg = json.loads((ROOT/'precision_registration.json').read_text())
    g = singletons()
    assert len(g) == cfg['candidate_count'] and [q['id'] for q in g] == cfg['candidate_ids']
    settings = dict(config=cfg, code={p.name:S.sha(p) for p in ROOT.glob('*.py')}, existing_package=S.fingerprint(fixture))
    digest = hashlib.sha256(S.encode(settings)).hexdigest()
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    S.jsonout(out/'run_identity.json', dict(fingerprint=digest, fixture=fixture, settings=settings))
    inputs = json.loads((S.ROOT/'inputs.json').read_text())
    months = ['2024-01'] if fixture else cfg['months']
    all_rows = []
    for m in months:
        part = out/(m+'.precision.json.gz')
        if part.exists():
            saved = json.loads(gzip.decompress(part.read_bytes()))
            assert json.loads((out/(m+'.sha256.json')).read_text())['sha256'] == S.sha(part), 'changed part'
            assert saved['fingerprint'] == digest
            audit(saved['raw'], saved['rows'])
        else:
            if fixture: d = S.fixture()
            else:
                item = next(x for x in inputs if x['month'] == m)
                with S.stage_inputs.open_verified(item) as source: d = S.load_data(source, compression='gzip')
            # Calculate only causal masks; no target/state labels are passed here.
            masks = S.masks(d, g)
            for cut in sorted(set([max(260, len(d['c'])//2), len(d['c'])-20])):
                prefix = S.masks({k: v[:cut] for k, v in d.items()}, g)
                for ident in masks: assert np.array_equal(prefix[ident], masks[ident][:cut]), ident
            eligible = np.array([i >= cfg['warmup_bars'] and S.month(t) == m for i, t in enumerate(d['dt'])])
            masks.update(BASELINE_ALL_BARS=np.ones(len(eligible), bool), BASELINE_NO_SIGNAL=np.zeros(len(eligible), bool))
            raw, rows = evaluate(d['c'], masks, eligible, cfg['horizon_bars'], cfg['gain_fraction'])
            raw['timestamps'] = d['dt'].tolist()
            for row in rows: row.update(asset=cfg['asset'], month=m)
            assert audit(raw, rows) == len(g)+2
            saved = dict(fingerprint=digest, raw=raw, rows=rows)
            S.atomic(part, gzip.compress(S.encode(saved), mtime=0))
            S.jsonout(out/(m+'.sha256.json'), dict(sha256=S.sha(part)))
        assert {r['candidate_id'] for r in saved['rows']} == {q['id'] for q in g} | {'BASELINE_ALL_BARS', 'BASELINE_NO_SIGNAL'}
        all_rows.extend(saved['rows'])
        print('VERIFIED_PART', m, flush=True)
        if stop_after and len(all_rows)//(len(g)+2) >= stop_after: return 'CHECKPOINT_ONLY'
    receipt = dict(status='SYNTHETIC_ONLY' if fixture else 'DISCOVERY_REVIEW_PENDING',
                   fingerprint=digest, rows=len(all_rows), months=months,
                   parts={m:S.sha(out/(m+'.precision.json.gz')) for m in months},
                   market_selection='none', independent_validation='not measured')
    S.jsonout(out/'precision_audit.json', receipt)
    S.jsonout(out/'precision_results.json', all_rows)
    report(out, receipt, all_rows)
    return receipt['status']


def report(out, receipt, rows):
    nm = 'غير مقاس — خارج مرحلة الإشارات'
    lines = ['# تقرير فحص دقة الإشارات', '',
             '**بيانات اصطناعية فقط**' if receipt['status']=='SYNTHETIC_ONLY' else '**اكتشاف تاريخي؛ ينتظر مراجعة القائد**', '',
             '1. السؤال: هل يتبع الإشارة ارتفاع إغلاق 0.5% خلال أربع شموع 15 دقيقة؟',
             '2. الصافي: '+nm, '3. الصفقات ونصيب الصفقة: '+nm, '4. عامل الربح: '+nm,
             '5. العمياء: غير مقاسة.', '6. مقابل الاحتفاظ: '+nm,
             '7. الحكم: لا اعتماد ولا اختيار فائز.', '8. التالي: مراجعة الأدلة وتعريف الهدف قبل ورقة تنفيذ طويلة.', '']
    sections = [
        ('1 — هوية التجربة', [('العملة','BTCUSDT'),('الفريم','15 دقيقة'),('الهدف','0.5% خلال الساعة التالية'),('الفترات',', '.join(receipt['months'])),('التحقق والعمياء','غير مقاسين')]),
        ('2 — المال', [(k,nm) for k in ['الصافي','عامل الربح','نصيب الصفقة','توقع الصفقة','الرسوم والانزلاق']]),
        ('3 — الصفقات', [(k,nm) for k in ['عدد الصفقات','نسبة الفوز المالي','متوسط الرابحة والخاسرة','نسبة الربح للخسارة','سلسلة الخسائر','مدة الاحتفاظ']]),
        ('4 — المخاطر', [(k,nm) for k in ['أقصى تراجع','مدة التراجع','أسوأ يوم','التعرض']]),
        ('5 — الجوار والثبات', [('الجوار ±20%','غير مقاس'),('الثبات','صف منفصل لكل نسخة وشهر؛ لا دمج يخفي الاختلاف')]),
        ('6 — الفترات والاحتفاظ', [('التعلم','اكتشاف فقط؛ سبق فحص الشهور'),('الامتحان','غير مقاس'),('العمياء','غير مقاسة'),('الاحتفاظ',nm)]),
        ('7 — الاعتماد', [('شروط المال',nm),('الدقة الممتازة','لم يثبت حد قبول أو حجم عينة بعد'),('الاعتماد','ممنوع في هذه الدفعة')])]
    for title, items in sections:
        lines += ['## '+title, '', '| البند | القيمة |', '|---|---|']
        lines += ['| '+k+' | '+v+' |' for k,v in items]
        lines.append('')
    lines += ['## نتائج الإشارات', '', '| الشهر | صفوف النسخ والأسس المقارنة |', '|---|---|']
    lines += [f'| {m} | {sum(r["month"]==m for r in rows)} |' for m in receipt['months']]
    lines += ['', 'الأعداد التفصيلية لكل نسخة في precision_results.json، والإشارات والأسعار اللازمة لإعادة العد في ملفات الشهر المضغوطة.',
              'الدقة = الصحيح ÷ (الصحيح + الكاذب). غير المكتمل خارج المقام ومعلن منفصلًا. الصفر في الإنذارات الكاذبة ليس ضمانًا مستقبليًا.',
              'تغطية فرص الهدف تخص سلاسل متجاورة من نوافذ مستقبلية ناجحة؛ ليست عدًا لحركات اقتصادية مستقلة. التأخير من أول نافذة ناجحة، وليس من قاع السعر.',
              'الهدف لا يقيس الهبوط قبل الصعود أو صلاحية الدخول المالي. فواصل Wilson وصفية؛ التداخل والبحث الواسع يمنعان استخدامها لإعلان تفوق.',
              '', '## بطاقة الحكم', 'تأكيد تقني فقط في التشغيل الاصطناعي؛ مراجعة القائد معلقة للقياس السوقي. الربحية غير مقاسة.',
              '', '## قاموس المصطلحات', '| المصطلح | معناه |', '|---|---|', '| الدقة | الصحيح ÷ الإشارات المحكوم عليها |', '| التغطية | فرص الهدف التي التقطت ÷ فرص الهدف |', '| المهلة | أربع شموع مكتملة بعد الإشارة |',
              '', '## قاموس التعبيرات', '| التعبير | العبارة المستخدمة |', '|---|---|', '| grid | قائمة النسخ المسجلة |', '| checkpoint | جزء محفوظ للاستئناف |',
              '', '## إعادة الاشتقاق', 'إعادة الأمر نفسه تتحقق من بصمة المصدر وبصمات الأجزاء وتعيد الحساب العددي المستقل من الخام. أمر الفحص الاصطناعي من مجلد الأدوات: python precision.py fixture --out OUTPUT. استخدم نفس OUTPUT ونفس المصدر للاستئناف.']
    S.atomic(out/'PRECISION_REPORT_AR.md', ('\n'.join(lines)+'\n').encode())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['fixture', 'measure'])
    parser.add_argument('--out', required=True)
    parser.add_argument('--stop-after', type=int)
    args = parser.parse_args()
    preflight(target=args.out)
    Path(args.out).mkdir(parents=True, exist_ok=True)
    with (Path(args.out)/'.precision.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        started = time.monotonic()
        result = run(args.out, args.mode == 'fixture', args.stop_after)
        print(json.dumps(dict(status=result, compute_seconds=time.monotonic()-started)))
