"""Post-hoc timing diagnosis of saved L0092 alerts; no new triggers or selection."""
import argparse, collections, gzip, hashlib, json, time
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--root', default='.')
p.add_argument('--out', default='l0092/timing-diagnosis')
a = p.parse_args(); root = Path(a.root); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
started = time.monotonic()
market = root/'l0092/market'; package = root/'l0090/package'
scope = json.loads((root/'l0092/scope.json').read_text())
for name, digest in scope['input_sha256'].items():
    assert hashlib.sha256((package/name).read_bytes()).hexdigest() == digest, name
alerts = json.loads((market/'alerts.json').read_text())
results = json.loads((market/'results.json').read_text())['rows']
raw = json.loads(gzip.decompress((package/'parent_raw.json.gz').read_bytes()))
lookup = collections.defaultdict(list)
for x in alerts: lookup[x['asset'], x['candidate'], x['period']].append(x)
# Independently reconcile all saved aggregate and quarterly counts, including zero alerts.
for row in results:
    for pi, metric in enumerate(row['periods']):
        xs = lookup[row['asset'], row['candidate'], pi]
        matched = [x['matched_onset'] for x in xs if x['matched_onset'] is not None]
        assert len(xs) == metric['signals'] and len(matched) == metric['matched_events']
        assert len(set(matched)) == len(matched)
        assert sorted(matched) == sorted(row['captured_onsets_by_period'][pi])
        for x in xs:
            assert x['bar'] in raw['assets'][row['asset']]['periods'][pi]['valid']
            if x['matched_onset'] is not None: assert abs(x['bar']-x['matched_onset']) <= 2

names = ['المطرقة2','المطرقة3','الابتلاع1','الابتلاع1.25','نجم الصباح0.5','نجم الصباح1']
categories = ['same_cci','after_cci_1or2_in_window','in_window_other_order','nearest_early_outside','nearest_late_outside','absent_within_12']
records = []; summaries = []
for asset, data in raw['assets'].items():
    for di, name in enumerate(names):
        counts = collections.Counter(); onset_counts = collections.Counter(); total = 0; caught = 0
        for pi, period in enumerate(data['periods']):
            candles = sorted(x['bar'] for x in lookup[asset, str(3*di), pi])
            cci_hits = {x['matched_onset']:x['bar'] for x in lookup[asset, 'CCI_CONTROL', pi] if x['matched_onset'] is not None}
            for event in period['events']:
                onset = event['onset']; total += 1
                nearby = [b for b in candles if abs(b-onset) <= 12]
                inside = [b for b in nearby if abs(b-onset) <= 2]
                nearest = min(nearby, key=lambda b:(abs(b-onset),b)) if nearby else None
                timing = 'in_window' if inside else 'absent' if nearest is None else 'early' if nearest < onset else 'late'
                onset_counts[timing] += 1
                cci = cci_hits.get(onset); cat = None
                if cci is not None:
                    caught += 1
                    if cci in inside: cat = categories[0]
                    elif any(b-cci in (1,2) for b in inside): cat = categories[1]
                    elif inside: cat = categories[2]
                    elif nearest is None: cat = categories[5]
                    elif nearest < onset: cat = categories[3]
                    else: cat = categories[4]
                    counts[cat] += 1
                    # Separate set-based partition check, independent of the priority chain.
                    flags = [cci in inside,
                             cci not in inside and bool(set(inside)&{cci+1,cci+2}),
                             bool(inside) and not bool(set(inside)&{cci,cci+1,cci+2}),
                             not inside and nearest is not None and nearest<onset,
                             not inside and nearest is not None and nearest>onset,
                             nearest is None]
                    assert sum(flags)==1 and categories[flags.index(True)] == cat
                records.append(dict(asset=asset,variant=di,period=pi,onset=onset,cci_matched_bar=cci,
                                    candle_bars_in_diagnostic_window=nearby,nearest_candle_lag=None if nearest is None else nearest-onset,
                                    onset_timing=timing,cci_category=cat))
        assert sum(counts.values()) == caught and sum(onset_counts.values()) == total
        summaries.append(dict(asset=asset,variant=di,name=name,events=total,cci_caught=caught,
                              cci_partition={k:counts[k] for k in categories},onset_partition=dict(onset_counts)))
aggregate=[]
for di,name in enumerate(names):
    ss=[s for s in summaries if s['variant']==di]
    aggregate.append(dict(name=name,events=sum(s['events'] for s in ss),cci_caught=sum(s['cci_caught'] for s in ss),
                          cci_partition={k:sum(s['cci_partition'][k] for s in ss) for k in categories},
                          onset_partition={k:sum(s['onset_partition'].get(k,0) for s in ss) for k in ['in_window','early','late','absent']}))
assert len(records)==636 and len(summaries)==18
payload=dict(status='PASS',classification='post-hoc descriptive diagnosis',new_strategy=False,selection=False,
             diagnostic_window='onset +/-12 bars; evaluation stays +/-2; only saved valid standalone alerts',
             denominator='each variant counts the same events separately; never sum variants as independent observations',
             source_commit='563d14325a872ea0682b7f3c25b5f1739cd63d17',
             input_hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [market/'alerts.json',market/'results.json',package/'parent_raw.json.gz']},
             rows=records,summaries=summaries,aggregate=aggregate,
             audit=dict(saved_metric_rows=57,event_variant_rows=636,partitions_checked=636,elapsed_seconds=time.monotonic()-started))
(out/'diagnosis.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
lines=['# تشخيص توقيت تأكيد الشموع بعد L0092','',
       'تحليل للأدلة المحفوظة فقط، دون تغيير إشارة أو اختيار مرشح أو نافذة نجاح. لا تجربة سوق جديدة.',
       'لكل نموذج106 أحداث، منها56 التقطها CCI. النتائج أدناه تعيد عد هذه الأحداث لكل نموذج؛ لا نجمع النماذج كعينات مستقلة.',
       'النافذة التشخيصية ±12 شمعة (±48 ساعة)؛ نافذة النجاح الأصلية ±2 لم تتغير. غياب النموذج يعني غياب نبضته المحفوظة ضمن النافذة، لا فشل جميع تأكيدات الشموع.',
       '','| النموذج | مع CCI بالشمعة نفسها | بعد CCI بـ1–2 داخل نافذة النجاح | قرب البداية بترتيب آخر | الأقرب مبكر خارج النافذة | الأقرب متأخر خارج النافذة | غائب ضمن ±12 |','|---|---:|---:|---:|---:|---:|---:|']
for s in aggregate: lines.append('|'+s['name']+'|'+'|'.join(str(s['cci_partition'][k]) for k in categories)+'|')
lines += ['','| النموذج | ظهر ضمن نافذة البداية | الأقرب مبكر | الأقرب متأخر | غائب ضمن ±12 |','|---|---:|---:|---:|---:|']
for s in aggregate: lines.append('|'+s['name']+'|'+'|'.join(str(s['onset_partition'][k]) for k in ['in_window','early','late','absent'])+'|')
lines += ['','## كل عملة منفصلة','| العملة | النموذج | أحداث CCI | متزامن | لاحق داخل النافذة | ترتيب آخر | مبكر | متأخر | غائب |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
for s in summaries: lines.append('|'+s['asset']+'|'+s['name']+'|'+str(s['cci_caught'])+'|'+'|'.join(str(s['cci_partition'][k]) for k in categories)+'|')
lines += ['','التمييز: هذه أعداد أحداث تحتوي نموذجًا؛ ليست دقة إشارات جديدة ولا إعادة حساب لأداء نافذة أوسع. لا يُرجع توقيت اكتمال نجم الصباح إلى أول شمعة فيه. الأقرب يختار المسافة الأقل، والتعادل للأسبق، داخل الفترة المؤهلة نفسها.',
          'التدقيق: إعادة مطابقة أعداد جميع57 صفًا وفتراتها والتنبيهات الصفرية، ومجموع كل تقسيم، وفحص مستقل بالتقاطعات لكل حدث CCI. المال والتحقق المستقبلي والاستدلال المصحح: not measured.',
          'الحكم: Defer؛ لا اعتماد ولا تعديل لنتائج L0092. التشخيص وصفي على تاريخ مكشوف، وتصنيف التوقيت يستخدم تسميات مستقبلية للتقييم فقط، ويحظر إدخاله في إشارة.',
          'الخطوة التالية: تصميم تأكيد سببي لحالة استرداد السعر المستمرة بدل اشتراط نبضة نموذج شموع نادر؛ تسجيل التعريف قبل قياس أي أداء جديد.',
          '', 'إعادة الحساب من نسخة الأدلة المحفوظة: `python l0092/diagnose_timing.py --root . --out l0092/timing-diagnosis`. بعد تنزيل ZIP المسجل والتحقق من بصمته، يوضع محتواه في l0092/market ومدخلات tools/l0090 في l0090/package.']
(out/'REPORT.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(aggregate=aggregate,audit=payload['audit']),ensure_ascii=False))
