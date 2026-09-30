#!/bin/bash

# إخبار الوكيل بمسار العمل المحلي
export OPENCRABS_HOME="/app/.opencrabs"

# التأكد من إنشاء المجلد
mkdir -p /app/.opencrabs

# تشغيل أمر تهيئة لإصلاح قاعدة البيانات إن كانت فارغة
./opencrabs init --yes || true

# 1. تشغيل الموزع الذكي في الخلفية
litellm --config litellm_config.yaml --port 4000 &

# 2. تشغيل الوكيل القائد 
./opencrabs daemon
