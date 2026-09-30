#!/bin/bash

# إخبار الوكيل باستخدام المجلد الحالي كمسار رئيسي له
export OPENCRABS_HOME="/app/.opencrabs"

# إنشاء المجلد الخاص بقاعدة بيانات الوكيل في المسار الجديد
mkdir -p /app/.opencrabs

# 1. تشغيل الموزع الذكي في الخلفية
litellm --config litellm_config.yaml --port 4000 &

# 2. تشغيل الوكيل القائد 
./opencrabs daemon
