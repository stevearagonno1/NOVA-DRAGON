#!/bin/bash

# تجهيز مجلد الجذور وقاعدة البيانات لكي تعثر عليه الأداة فوراً دون أخطاء
mkdir -p /root/.opencrabs/backups
if [ ! -f /root/.opencrabs/opencrabs.db ]; then
    touch /root/.opencrabs/opencrabs.db
fi

# تشغيل الموزع الذكي على المنفذ 10000 المطلوب من منصة Render
litellm --config litellm_config.yaml --port 10000 &

# تشغيل الوكيل القائد
./opencrabs daemon
