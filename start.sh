#!/bin/bash

# إنشاء المجلد الخاص بقاعدة بيانات الوكيل لتجنب خطأ التخزين
mkdir -p /root/.opencrabs

# 1. تشغيل الموزع الذكي في الخلفية
litellm --config litellm_config.yaml --port 4000 &

# 2. تشغيل الوكيل القائد 
./opencrabs daemon
