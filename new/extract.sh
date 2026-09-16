#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  NOVA — إعادة اشتقاق شجرة الفحص new/ من الحزمة الأم بأمر واحد
#  السبب: بيئة أرينا تُعاد تدويرها بين الجولات؛ ما ليس متعقَّباً في git
#  لا يبقى — والحزمة الأم nova_upload_bundle.tar.gz متعقَّبة في main.
#  الاستخدام (من جذر المستودع):
#      bash new/extract.sh            # عادي — يتخطى الموجود
#      bash new/extract.sh --force    # مسح شجرة الاستخراج وإعادة الفك من الصفر
#  العزل new/_quarantine/ لا يُمس أبداً في أي حالة.
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

SHA_REQUIRED="31d64494ec40e4cb65ea5f90fa11a68cfc2ba5324d0abdaf8a0b3b49086349f3"
BUNDLE="nova_upload_bundle.tar.gz"

# ١) بوابة البصمة — لا عمل إلا بمطابقة تامة
echo "[1/5] بوابة البصمة..."
SHA_GOT=$(sha256sum "$BUNDLE" | awk '{print $1}')
if [ "$SHA_GOT" != "$SHA_REQUIRED" ]; then
  echo "توقف: البصمة غير مطابقة!" >&2
  echo "المطلوب: $SHA_REQUIRED" >&2
  echo "الموجود: $SHA_GOT" >&2
  exit 1
fi
echo "  مطابقة ✓"

# ٢) فك الحزمة الأم
if [ "${1:-}" = "--force" ]; then
  echo "[2/5] --force: مسح شجرة الاستخراج وإعادة الفك..."
  rm -rf new/NOVA_bin_pending
fi
if [ ! -d new/NOVA_bin_pending ]; then
  echo "[2/5] فك الحزمة الأم..."
  mkdir -p new
  tar xzf "$BUNDLE" -C new/
else
  echo "[2/5] شجرة الاستخراج موجودة — تخطٍّ"
fi

# ٣) فك كل الأكياس الداخلية إلى <الاسم>_X — جولة بعد جولة حتى النفاد
#    (يلتقط الكيس المتداخل داخل NOVA_نقل_كامل_X تلقائياً)
echo "[3/5] فك الأكياس الداخلية..."
cd new
pass=0
while :; do
  pass=$((pass + 1))
  new_ones=0
  while IFS= read -r -d '' z; do
    dir="${z%.zip}_X"
    [ -d "$dir" ] && continue
    mkdir -p "$dir"
    unzip -o -q "$z" -d "$dir"
    new_ones=$((new_ones + 1))
  done < <(find . -iname "*.zip" -not -path "./_quarantine/*" -print0)
  echo "  الجولة $pass: فُك $new_ones كيساً"
  [ "$new_ones" -eq 0 ] && break
done
cd ..

# ٤) تصحيح أسماء الملفات العربية المشوهة من unzip (صيغة #U060c)
echo "[4/5] تصحيح الأسماء العربية المشوهة..."
python3 - <<'PYEOF'
import os, re
pat = re.compile(r"#U([0-9a-fA-F]{4})")
n = 0
for root, dirs, files in os.walk("new"):
    if "_quarantine" in root.split(os.sep):
        continue
    for name in files + dirs:
        if "#U" in name:
            new = pat.sub(lambda m: chr(int(m.group(1), 16)), name)
            if new != name:
                os.rename(os.path.join(root, name), os.path.join(root, new))
                n += 1
print(f"  صُحح {n} اسماً")
PYEOF

# ٥) الإحصاء + العزل — يعيد توليد CENSUS.md و_quarantine/MAP.md (متكرر بأمان)
echo "[5/5] الإحصاء والعزل..."
python3 new/census.py

echo "═══ تمت إعادة الاشتقاق كاملة ═══"
