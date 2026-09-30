#!/bin/bash

# إنشاء المجلدات الأساسية ومسار النسخ الاحتياطية للوكيل
mkdir -p /root/.opencrabs/backups

# تهيئة ملف قاعدة بيانات فارغ لتجاوز خطأ فحص السلامة الأولي
if [ ! -f /root/.opencrabs/opencrabs.db ]; then
    touch /root/.opencrabs/opencrabs.db
fi

# 1. تشغيل الموزع الذكي (LiteLLM) في الخلفية على المنفذ 4000
litellm --config litellm_config.yaml --port 4000 &

# 2. تشغيل الوكيل القائد (OpenCrabs)
./opencrabs daemon
