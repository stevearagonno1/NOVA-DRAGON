import os, sys, re, hashlib, subprocess, shutil
# NOVA V8 — ينظّم incoming/ في مجلدات مرتبة، ويشطب المكرر بالبصمة، ويكتب INDEX.md
# python3 tools/organize_incoming.py            -> معاينة فقط
# python3 tools/organize_incoming.py --apply    -> ينفّذ ويحفظ commit محلي (لا يرفع)
APPLY = '--apply' in sys.argv
SRC = 'incoming'
RULES = [('nova_v8_out', 'archive/research_variants'), ('nova_v8/', 'archive/code_snapshot'),
         ('nova_pack', 'archive/code_snapshot'), ('جميع اصدارات البوت', 'bot_versions'),
         ('اصدارات متنوعه', 'bot_versions'), ('.parquet', 'data'), ('.csv', 'data'),
         ('الدستور', 'docs/constitution'), ('فرض', 'hypotheses'), ('نخبة', 'hypotheses'),
         ('لوحة_خط', 'hypotheses'), ('محرك_الواجهة', 'docs/designs'), ('المخطط_الشامل', 'docs/designs'),
         ('دليل_الرموز', 'docs/designs'), ('عقد_الترجمة', 'docs/designs'), ('وثيقة_تفويض', 'docs/designs'),
         ('تصميم', 'docs/designs'), ('استراتيجيتان', 'docs/designs'),
         ('نتائج', 'docs/reports'), ('تقرير', 'docs/reports'), ('مراجعة', 'docs/reports'),
         ('ملخص', 'docs/reports'), ('تحليل', 'docs/reports'), ('استشارة', 'docs/reports'),
         ('سجل_العمل', 'docs/reports'), ('الجدول_الختامي', 'docs/reports'), ('ابد_أولا', 'docs/reports'),
         ('سجل_المحادثة', 'docs/conversations'), ('وثيقة_السياق', 'docs/conversations'),
         ('رسالة_', 'docs/conversations'), ('نجوم', 'docs/conversations'),
         ('.env', 'archive/quarantine'), ('credential', 'archive/quarantine'),
         ('.py', 'code_drafts'), ('.sh', 'code_drafts'),
         ('.zip', 'archive/binary'), ('.rar', 'archive/binary'), ('.pdf', 'archive/binary'),
         ('.docx', 'archive/binary'), ('.doc', 'archive/binary')]
STRIP = r'^(workspace|extracted|nova|nova_pack|uploads|crypto_archive|_k3|tools|جميع اصدارات البوت|اصدارات متنوعه)/'
TEXT = ('.txt', '.md', '.py', '.sh', '.log', '.csv', '.json')
BIG = ('crypto_archive/', 'research/nova_v8_out/')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def files(root):
    out = []
    if not os.path.isdir(root):
        return out
    for dp, ds, fs in os.walk(root):
        ds[:] = [d for d in ds if d not in ('.git', '__pycache__', '.ipynb_checkpoints')]
        out += [os.path.relpath(os.path.join(dp, f), root) for f in fs]
    return out


def dest_of(rel):
    low = rel.lower()
    for k, d in RULES:
        if k.lower() in low:
            return d
    return 'docs/misc'


def head(p):
    try:
        with open(p, encoding='utf-8', errors='replace') as f:
            for l in f:
                t = l.strip().lstrip('#*-= ').replace('|', '/')
                if len(t) >= 3:
                    return t[:90]
    except Exception:
        pass
    return ''


def hum(n):
    return '%.1fM' % (n / 1048576.0) if n >= 1048576 else '%dK' % max(1, n // 1024)


repo = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip()
if not repo:
    print('شغّله من داخل ~/nova'); sys.exit(2)
os.chdir(repo)
if not os.path.isdir(SRC):
    print('لا يوجد مجلد %s — انتهى التنظيم سابقاً؟' % SRC); sys.exit(0)

J = set(r for r in files(SRC) if os.path.basename(r) in ('.DS_Store', 'Thumbs.db')
        or r.endswith(('.pyc', '.pyo')) or '__matrix__' in r)
junk = list(J)
for r in junk:
    if APPLY:
        os.remove(os.path.join(SRC, r))
if junk:
    print('نفايات حُذفت: %d' % len(junk))

index = {}
for r in files('.'):
    if not r.startswith(SRC + os.sep):
        try:
            index.setdefault(sha(r), r)
        except Exception:
            pass

moves, same_repo, same_inner, seen = [], [], {}, {}
for r in sorted(set(files(SRC)) - J):
    p = os.path.join(SRC, r)
    try:
        h = sha(p)
    except Exception:
        continue
    sz = os.path.getsize(p)
    if h in index:
        same_repo.append((r, index[h], sz)); continue
    if h in seen:
        same_inner.setdefault(h, []).append(r); continue
    seen[h] = r
    t = r.replace('\\', '/')
    while True:
        n = re.sub(STRIP, '', t)
        if n == t:
            break
        t = n
    moves.append([r, os.path.join(dest_of(r), t), sz, h])

taken = set(index.values())


def free(d, src):
    c, n = d, 1
    par = os.path.basename(os.path.dirname(src)) or 'x'
    while c in taken or os.path.exists(c):
        b = os.path.basename(d)
        c = os.path.join(os.path.dirname(d), (par + '__' + b) if n == 1
                         else (par + '__' + os.path.splitext(b)[0] + '~%d' % n + os.path.splitext(b)[1]))
        n += 1
    taken.add(c)
    return c


for m in moves:
    m[1] = free(m[1], m[0])

if APPLY:
    for r, _k, _s in same_repo:
        os.remove(os.path.join(SRC, r))
    for h, rs in same_inner.items():
        for r in rs:
            p = os.path.join(SRC, r)
            if os.path.exists(p):
                os.remove(p)
    for r, d, _s, _h in moves:
        p = os.path.join(SRC, r)
        if os.path.exists(p):
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.move(p, d)
    try:
        shutil.rmtree(SRC)
    except Exception:
        pass
    now = set()
    for r in files('.'):
        try:
            now.add(sha(r))
        except Exception:
            pass
    missing = [m[3] for m in moves if m[3] not in now]
else:
    missing = []

buckets = {}
if APPLY:
    for r in files('.'):
        if not r.startswith(BIG):
            buckets.setdefault(os.path.dirname(r) or '.', []).append(r)
    base = 'research/nova_v8_out'
    if os.path.isdir(base):
        s = {}
        for r in files(base):
            k = base + '/' + r.split(os.sep)[0]
            e = s.setdefault(k, [0, 0])
            e[0] += 1
            e[1] += os.path.getsize(os.path.join(base, r))
        b = buckets.setdefault('(أرشيف النتائج — على مستوى المجلد)', [])
        b += ['`%s/` — %d ملف (%s)' % (k, v[0], hum(v[1])) for k, v in sorted(s.items())]
else:
    for r, d, _s, _h in moves:
        buckets.setdefault(os.path.dirname(d), []).append(d)

L = ['# فهرس المستودع — NOVA V8', '',
     'الهيكل من `tools/organize_incoming.py`. المكرر الحرفي (نفس sha256) شُطب، وغيره نُقل بمساره — ولا معلومة ضاعت.',
     'آخر تنظيم: 2026-09-14 | الملفات الواردة: %d | منقولة: %d | محذوفة لتطابقها: %d' %
     (len(moves) + len(same_repo) + sum(len(v) for v in same_inner.values()), len(moves),
      len(same_repo) + sum(len(v) for v in same_inner.values())), '',
     '## خريطة المجلدات', '', '| المجلد | ما فيه |', '|---|---|',
     '| `nova_v8` | الكود المجمّد للمحرك — لا يُعدَّل إلا بقرار D |',
     '| `docs/constitution` | دستورك: الأعلى والتشغيلي |',
     '| `docs/designs` | التصاميم: محرك الواجهة، المخطط الشامل، دليل الرموز، عقد الترجمة |',
     '| `docs/reports` | تقارير التدقيق والنتائج والمراجعات |',
     '| `docs/conversations` | سجلات المحادثات ورسائل التوجيه (ذاكرة القرارات) |',
     '| `docs/lanes` | الحارات: كل تجربة = ملف فيه عقده وحكمه |',
     '| `hypotheses` | الفرضيات: الـ212 + النخبة + لوحة الخط + عقد المصنع |',
     '| `bot_versions` | كل نسخ البوت القديمة — تاريخ محفوظ، لا كود حيّ |',
     '| `data` | باركيه صغير أعيد منه حساب النتائج |',
     '| `research` | نتائج التشغيل الحقيقية (الأرشيف) |',
     '| `tools` | أدواتنا: الفحص، البروبي، جدول الأرشيف، المنظّم |',
     '| `crypto_archive` | البيانات الضخمة (BTC 1m لخمس سنوات) |',
     '| `code_drafts` | مسودات كود مستقلة ليست من المحرك |',
     '| `archive` | القديم وغير المطابق — محفوظ لا مربوط |', '', '## كل ملف بمكانه', '']
for d in sorted(buckets):
    it = sorted(buckets[d])
    L.append('### `%s` (%d)' % (d, len(it)))
    L.append('')
    for r in it:
        if r.startswith('`'):
            L.append('- ' + r); continue
        sz, desc = 0, ''
        if APPLY:
            try:
                sz = os.path.getsize(r)
            except Exception:
                pass
            if r.lower().endswith(TEXT) and sz < 3000000:
                desc = head(r)
        L.append('- `%s` (%s) %s' % (r, hum(sz), ('— ' + desc) if desc else ''))
    L.append('')
if APPLY:
    open('INDEX.md', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    R = ['# تقرير التنظيم — 2026-09-14', '',
         'وارد: %d | منقول: %d | محذوف لتطابق البصمة: %d | مفقودات بعد التحقق: %d (يجب صفر)' %
         (len(moves) + len(same_repo) + sum(len(v) for v in same_inner.values()), len(moves),
          len(same_repo) + sum(len(v) for v in same_inner.values()), len(missing)), '',
         '## 1) مطابق لملف موجود في المستودع (الحذف بلا خسارة)', '']
    for r, k, s in same_repo[:250]:
        R.append('- `%s` == `%s` (%s)' % (r, k, hum(s)))
    if len(same_repo) > 250:
        R.append('- ... و%d ملفاً آخر بنفس الحالة' % (len(same_repo) - 250))
    R += ['', '## 2) نسخة ثانية من نفس المحتوى داخل الوارد (بقي الأول)', '']
    for h, rs in list(same_inner.items())[:200]:
        R.append('- بقي `%s` — حُذف: %s' % (seen.get(h, '?'), ', '.join('`%s`' % x for x in rs[:5])))
    R += ['', '## 3) محتويات مختلفة أُبقيت (مجردة من التكرار)', '']
    for r, d, s, h in moves[:60]:
        R.append('- `%s` <- `%s` (%s)' % (d, r, hum(s)))
    os.makedirs('docs/reports', exist_ok=True)
    open('docs/reports/ORGANIZATION-2026-09-14.md', 'w', encoding='utf-8').write('\n'.join(R) + '\n')

print('== %s ==' % ('تنفيذ' if APPLY else 'معاينة — لن يتغير شيء'))
print('منقول: %d | محذوف لتطابق البصمة: %d (منه %d مطابق لموجود) | نفايات: %d' %
      (len(moves), len(same_repo) + sum(len(v) for v in same_inner.values()), len(same_repo), len(junk)))
for b in sorted({os.path.dirname(d) for _r, d, _s, _h in moves}):
    print('   %-34s %d' % (b, sum(1 for _r, d2, _s, _h in moves if os.path.dirname(d2) == b)))
print('التحقق — مفقودات: %d %s' % (len(missing), '✓' if not missing else '⛔ أوقف ولا ترفع'))
if APPLY and not missing:
    ps = [x for x in ['INDEX.md', SRC, 'docs', 'hypotheses', 'bot_versions', 'data',
                      'code_drafts', 'archive', 'tools'] if os.path.exists(x)]
    r = subprocess.run(['git', 'add', '-A', '--'] + ps, capture_output=True, text=True)
    ch = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()
    if r.returncode != 0 or not ch:
        subprocess.run(['git', 'add', '-A'], capture_output=True)
        ch = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()
    if ch:
        subprocess.run(['git', 'commit', '-q', '-m', 'تنظيم incoming: %d ملف + شطب %d مكرر + INDEX.md'
                        % (len(moves), len(same_repo) + sum(len(v) for v in same_inner.values()))],
                       capture_output=True)
        print('حفظ محلي %s — لم يُرفع. للتراجع: git revert --no-edit HEAD' %
              subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip())
