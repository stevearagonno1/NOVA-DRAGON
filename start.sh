#!/bin/bash

# إخبار الوكيل بمسار العمل المحلي
export OPENCRABS_HOME="/app/.opencrabs"
mkdir -p /app/.opencrabs

# تشغيل الموزع الذكي ليطابق المنفذ المطلوب من Render (10000)
litellm --config litellm_config.yaml --port 10000 &

# تشغيل الوكيل القائد
./opencrabs daemon
