#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  NOVA — دمج فرع الجلسة إلى main من تيرمكس (بيد المستخدم وحده)
#  الحكم الدستوري د-١: الوكيل ممنوع من الدمج — هذا حقك وحدك.
#
#  الاستخدام من ~/nova في تيرمكس:
#     bash tools/merge_main.sh                # يدمج فرع الجلسة الحالي الافتراضي
#     bash tools/merge_main.sh <اسم-فرع>      # لدمج فرع آخر بالاسم
#     bash tools/merge_main.sh --list         # عرض الفروع فقط (بلا أي دمج)
# ════════════════════════════════════════════════════════════════
set -euo pipefail

BRANCH="${1:-arena/01a0a9f3-nova-dragon}"
cd "$(dirname "$0")/.."

echo "[١] جلب آخر حالة من GitHub..."
git fetch origin

if [ "$BRANCH" = "--list" ]; then
  echo "الفروع المتاحة:"
  git branch -r | grep -v HEAD || true
  echo "انتهى العرض — لم يُدمج شيء."
  exit 0
fi

if ! git rev-parse --verify --quiet "origin/$BRANCH" >/dev/null; then
  echo "✗ الفرص غير موجود: $BRANCH"
  echo "الفروع المتاحة:"
  git branch -r | grep -v HEAD || true
  echo "شغّله مرة أخرى باسم فرع من القائمة أعلاه."
  exit 1
fi

echo "[٢] الانتقال إلى main وتحديثه..."
git checkout main
git pull --ff-only origin main

echo "[٣] ما سيُدمج — آخر التزامات $BRANCH غير الموجودة في main:"
git log --oneline "origin/main..origin/$BRANCH" | head -10 || true

echo "[٤] الدمج..."
if ! git merge --no-ff "origin/$BRANCH" -m "دمج $BRANCH إلى main — من تيرمكس بأمر المستخدم"; then
  git merge --abort || true
  echo "✗ حدث تعارض — أُلغي الدمج بأمان. أرسل هذا الخرج كاملاً للوكيل."
  exit 1
fi

echo "[٥] الرفع إلى GitHub..."
git push origin main

echo ""
echo "✓ تم الدمج والرفع بنجاح — أرسل آخر ٤ أسطر للوكيل:"
git log --oneline -3
echo "والفروع المحلية:"
git branch --show-current
