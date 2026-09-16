#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════
#  NOVA — تنقية حزمة الرفع من المفاتيح (بما داخل الأكياس وملفات وورد)
#
#  القاعدة الحاكمة: لا يُحجب شيء إلا إذا كانت القيمة نفسها على شكل سرّ حقيقي.
#  هذا يمنع جرح الأسطر السليمة مثل:  os.getenv("BINANCE_API_KEY", "")
#  (تلك الجروح هي نفسها التي أصابت نسخ المستودع القديمة — ١٦١ موضعاً في ٦١ ملفاً)
#
#  الاستخدام (من جذر المستودع):
#      python3 tools/redact_bundle_keys.py                       # ينشئ الحزمة النقية جنب الأصل
#      python3 tools/redact_bundle_keys.py <src.tar.gz> <dst>    # مسارات صريحة
#      python3 tools/redact_bundle_keys.py --check <tar.gz>      # فحص فقط، بلا كتابة
#
#  ملاحظة: إعادة البناء تغيّر بصمة sha256 للحزمة ⇒ يجب تحديث ثلاث مراجع معها:
#      new/extract.sh (بوابة SHA_REQUIRED) · new/CENSUS.md · new/census.py
#  والتنقية لا تحذف الأسرار من تاريخ git ولا من النسخة المنشورة — التدوير هو الحل.
# ═══════════════════════════════════════════════════════════════════════
import os, re, io, sys, gzip, tarfile, zipfile, hashlib, shutil, tempfile

TOKEN = "__REDACTED__"
SECRET_VARS = ("BINANCE_API_KEY", "BINANCE_API_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_TOKEN",
               "TELEGRAM_CHAT_ID", "CHAT_ID", "GEMINI_API_KEY", "OPENAI_API_KEY",
               "API_SECRET", "SECRET_KEY")
ASSIGN = re.compile(r"\b(?P<key>" + "|".join(SECRET_VARS) + r")\b(?P<sep>\s*=\s*)"
                    r"(?P<q>['\"]?)(?P<val>[^'\"\n]*)(?P=q)")
SHAPES = [
    ("تيليجرام",     re.compile(r"\b\d{8,10}:[A-Za-z0-9_\-]{30,}\b")),
    ("جيميناي-AIza", re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}\b")),
    ("جيميناي-AQ",   re.compile(r"\bAQ\.[A-Za-z0-9_\-]{20,}\b")),
    ("بينانس-64",    re.compile(r"\b[A-Za-z0-9]{64}\b")),
]
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CODE_HINT = re.compile(r"[()\[\]{}]|getenv|environ|strip|import|None|True|False|f\"|f'")


def is_secret_value(key, val):
    v = val.strip()
    if len(v) < 6 or v == TOKEN or v.startswith(("$", "{")):
        return False
    if CODE_HINT.search(v):                      # ← يحمي الكود السليم من الجرح
        return False
    if key in ("CHAT_ID", "TELEGRAM_CHAT_ID"):
        return v.isdigit()
    return any(rx.search(v) for _n, rx in SHAPES) or \
           (len(v) >= 32 and re.fullmatch(r"[A-Za-z0-9_\-]+", v))


def clean_text(t, where, report):
    n = 0

    def rep(m):
        nonlocal n
        if not is_secret_value(m.group("key"), m.group("val")):
            return m.group(0)
        n += 1
        return f'{m.group("key")}{m.group("sep")}{m.group("q")}{TOKEN}{m.group("q")}'

    t2 = ASSIGN.sub(rep, t)
    for _name, rx in SHAPES:
        t2, k = rx.subn(TOKEN, t2)
        n += k
    if n:
        report.append((where, n))
    return (t2 if n else t), n


def clean_bytes(data, where, report):
    try:
        t = data.decode("utf-8")
    except Exception:
        return data, 0                            # ثنائي — لا يُمس
    t2, n = clean_text(t, where, report)
    return (t2.encode("utf-8") if n else data), n


def clean_zip_bytes(zb, where, report):
    zin = zipfile.ZipFile(io.BytesIO(zb))
    out = io.BytesIO()
    changed = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            data = zin.read(it.filename)
            name = f"{where}!{it.filename}"
            if data[:2] == b"PK":
                data, k = clean_zip_bytes(data, name, report)
            else:
                data, k = clean_bytes(data, name, report)
            changed += k
            ni = zipfile.ZipInfo(it.filename, date_time=it.date_time)
            ni.compress_type = it.compress_type
            ni.external_attr = it.external_attr
            zout.writestr(ni, data)
    return (out.getvalue() if changed else zb), changed



def pick_workdir(candidates=None):
    """يختار أول مجلد قابل للكتابة فعلاً — تيرمكس لا يملك /tmp ولا يقبل الكتابة فيه."""
    if candidates is None:
        c = []
        if os.environ.get("NOVA_REDACT_WORK"):
            c.append(os.environ["NOVA_REDACT_WORK"])
        if os.environ.get("TMPDIR"):
            c.append(os.path.join(os.environ["TMPDIR"], "_redact_work"))
        c.append(os.path.join(tempfile.gettempdir(), "_redact_work"))
        prefix = os.environ.get("PREFIX")
        if prefix:
            c.append(os.path.join(prefix, "tmp", "_redact_work"))
        c.append(os.path.abspath(".redact_work"))          # داخل المستودع — يُحذف في النهاية
        candidates = c
    for cand in candidates:
        try:
            os.makedirs(cand, exist_ok=True)
            probe = os.path.join(cand, ".w")
            with open(probe, "w") as f:
                f.write("ok")
            os.remove(probe)
            return cand
        except OSError:
            continue
    raise OSError("لا يوجد مجلد عمل قابل للكتابة — حدّد NOVA_REDACT_WORK يدوياً")


def scan_text(t):
    hits = []
    for m in ASSIGN.finditer(t):
        if is_secret_value(m.group("key"), m.group("val")):
            hits.append("إسناد " + m.group("key"))
    for name, rx in SHAPES:
        for m in rx.finditer(t):
            v = m.group(0)
            if name == "بينانس-64" and HEX64.match(v):
                ctx = t[max(0, m.start() - 40):m.start()].lower()
                if "sha" in ctx or "hash" in ctx or "بصمة" in ctx:
                    continue                      # بصمة موثقة لا مفتاح
            hits.append(name)
    return hits


def walk_tar(path):
    out = {}
    with tarfile.open(path) as t:
        for m in t.getmembers():
            if not m.isfile():
                continue
            stack = [(m.name, t.extractfile(m).read())]
            while stack:
                n, d = stack.pop()
                if d[:2] == b"PK":
                    z = zipfile.ZipFile(io.BytesIO(d))
                    for it in z.infolist():
                        stack.append((f"{n}!{it.filename}", z.read(it.filename)))
                else:
                    try:
                        out[n] = d.decode("utf-8")
                    except Exception:
                        pass
    return out


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    args = [a for a in sys.argv[1:]]
    if args and args[0] == "--check":
        path = args[1] if len(args) > 1 else "nova_upload_bundle.tar.gz"
        bad = {n: scan_text(t) for n, t in walk_tar(path).items()}
        bad = {n: h for n, h in bad.items() if h}
        print(f"فحص {path}")
        print(f"  مداخل نصية: {len(walk_tar(path))} · ملفات فيها أسرار: {len(bad)}"
              f" · مواضع: {sum(len(h) for h in bad.values())}")
        for n in sorted(bad):
            print("   ", n)
        return 1 if bad else 0

    src = args[0] if len(args) > 0 else "nova_upload_bundle.tar.gz"
    dst = args[1] if len(args) > 1 else "nova_upload_bundle.clean.tar.gz"
    work = pick_workdir()
    report = []

    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    with tarfile.open(src) as t:
        t.extractall(work)

    for root, dirs, files in os.walk(work):
        for name in sorted(files):
            p = os.path.join(root, name)
            rel = os.path.relpath(p, work)
            data = open(p, "rb").read()
            if data[:2] == b"PK":
                new, k = clean_zip_bytes(data, rel, report)
            else:
                new, k = clean_bytes(data, rel, report)
            if k:
                open(p, "wb").write(new)

    if os.path.exists(dst):
        os.remove(dst)

    def norm(ti):
        ti.mtime = 0
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = "user"
        return ti

    # بناء حتمي: tar بلا بصمات زمنية + gzip بـ mtime=0 ⇒ بصمة sha256 ثابتة بين التشغيلات
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as out:
        for root, dirs, files in os.walk(work):
            dirs.sort(); files.sort()
            for name in files:
                p = os.path.join(root, name)
                out.add(p, arcname=os.path.relpath(p, work), recursive=False, filter=norm)
    with open(dst, "wb") as fh:
        with gzip.GzipFile(filename="", mode="wb", fileobj=fh, mtime=0) as gz:
            gz.write(raw.getvalue())

    print(f"الأصلية : {os.path.getsize(src):,} بايت · sha256 {sha(src)}")
    print(f"النقية   : {os.path.getsize(dst):,} بايت · sha256 {sha(dst)}")
    print(f"مواضع حُجبت: {sum(n for _w, n in report)} في {len(report)} مدخلاً")
    for w, n in sorted(report):
        print(f"   {n:>2}  {w}")

    shutil.rmtree(work, ignore_errors=True)          # نظافة: لا بقايا بعد الجولة

    # تحقق ذاتي إلزامي: لا سرّ يبقى في الناتج
    bad = {n: h for n, h in ((n, scan_text(t)) for n, t in walk_tar(dst).items()) if h}
    print(f"التحقق الذاتي: ملفات فيها أسرار بعد التنقية = {len(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
