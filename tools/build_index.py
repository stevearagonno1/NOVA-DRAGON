#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# توليد فهرس المستودع INDEX.md من شجرة git — أمر واحد قابل لإعادة التشغيل (البند ١٠)
# الاستخدام: python3 tools/build_index.py (الأسماء من الشجرة والأحجام من مجلد العمل)
import subprocess, os, datetime
CURATED = {
 "bot/":"البوت الجاهز للتشغيل — التاج V7.0.1 النقي (NOVA.py + النسب + شهادة الجهوزية)",
 "live/":"التداول الحي: القواعد الملزمة + وثيقة الربط + توثيق المنفِّذ F-197",
 "nova_v8/":"المحرك المقدَّس — لا يُعدَّل إلا بقرار D (البند ١١)",
 "data/":"باركيه البيانات + MANIFEST.md المقدَّس — لا يُمس",
 "crypto_archive/":"البيانات الضخمة (عملات 1m — أغلبيتها ٥ سنوات) — لا يُمس",
 "tools/":"كل أدوات المستودع بلا استثناء: الفحص والتنظيم والدمج والخريطة",
 "docs/":"الوثائق: الست الدستورية في المستوى الأول + constitution/ designs/ lanes/ security/",
 "docs/constitution/":"مرايا الدستور",
 "docs/designs/":"التصاميم: المخطط الشامل ومحرك الواجهة وعقود الترجمة",
 "docs/lanes/":"حارات البحث الحيّة — كل تجربة ملف (تُنشأ عبر tools/new_lane.py)",
 "docs/security/":"الأمن: دليل تدوير المفاتيح",
 "new/":"بوابة استقبال الحزم: أداتا الإحصاء والاستخراج + الشهادات + خريطة المعزل السري",
 "history/":"المظلة الأرشيفية — كل مادة تاريخية/اختبارية (لا يُعاد ترتيبه داخلياً)",
 "old/":"المتقاعد: المسودات + مكررات الحزمة القابلة للاشتقاق بأمر واحد"}
LIVE = ["bot/","live/","tools/","new/","docs/"]
def parent(p):
    i = p.rfind("/"); return p[:i+1] if i >= 0 else ""
def kb(p):
    try: return os.path.getsize(p)//1024
    except OSError: return 0
out = subprocess.run(["git","-c","core.quotepath=false","ls-tree","-r","--full-tree","HEAD"],capture_output=True,text=True,check=True).stdout
paths = [l.split("\t",1)[1] for l in out.splitlines() if "\t" in l]
tops, bydir, sub2 = {}, {}, {}
for p in paths:
    t = p.split("/",1)[0]+("/" if "/" in p else ""); tops[t] = tops.get(t,0)+1
    d = parent(p)
    if d: bydir[d] = bydir.get(d,0)+1
    if p.startswith(("history/","old/")):
        q = p.split("/",2); k = q[0]+"/" if len(q)==2 else q[0]+"/"+q[1]+"/"
        sub2[k] = sub2.get(k,0)+1
today = datetime.date.today().isoformat()
try:
    old = open("INDEX.md",encoding="utf-8").read()
    narrative = old.split("\n## خريطة المجلدات")[0].rstrip()+"\n"
except FileNotFoundError:
    narrative = "# فهرس المستودع — NOVA DRAGON\n"
narrative += f"\nتحديث الصقل النهائي {today} (D‑0030): الفهرس يُولَّد بأمر واحد `python3 tools/build_index.py` — البنية مجمدة، والسرد التاريخي أعلاه محفوظ بلا مساس.\n"
L = [narrative,"\n## خريطة المجلدات\n","| البيت | الملفات | ما فيه |","|---|---|---|"]
for d in ["bot/","live/","nova_v8/","data/","crypto_archive/","tools/","docs/","new/","history/","old/"]:
    L.append(f"| `{d}` | {tops.get(d,0)} | {CURATED[d]} |")
L.append("| ملفات الجذر | "+str(sum(1 for p in paths if "/" not in p))+" | طبقة الدخول الدستورية + هذا الفهرس |")
L.append("\n## الملفات التشغيلية (الجذر والبيوت الحيّة)\n")
L.append("**الجذر:** "+" · ".join(f"`{p}`" for p in sorted(paths) if "/" not in p))
for d in LIVE:
    L.append(f"\n**`{d}`** ({tops.get(d,0)} ملفاً):")
    for p in sorted(paths):
        if parent(p) == d: L.append(f"- `{p}` ({kb(p)}K)")
for s in ["docs/constitution/","docs/designs/","docs/lanes/","docs/security/"]:
    L.append(f"\n**`{s}`** ({bydir.get(s,0)}): "+" · ".join(f"`{p.split('/')[-1]}`" for p in sorted(paths) if parent(p)==s))
L.append("\n## الأرشيف بالأرقام (تراكمي — لا يُعاد ترتيبه)\n")
L.append("| المجموعة | ملفات |"); L.append("|---|---|")
for d in sorted(sub2): L.append(f"| `{d}` | {sub2[d]} |")
L.append(f"| **الإجمالي المتعقَّب** | **{len(paths)}** |")
L.append("\n---\n*وُلِّد آلياً بأمر `python3 tools/build_index.py` — البند ١٠: كل رقم قابل لإعادة الاشتقاق.*")
open("INDEX.md","w",encoding="utf-8").write("\n".join(L)+"\n")
print(f"OK INDEX.md: {len(paths)} tracked files")
