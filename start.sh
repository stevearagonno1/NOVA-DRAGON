#!/bin/bash
# 1. تشغيل الموزع الذكي في الخلفية على المنفذ 4000
litellm --config litellm_config.yaml --port 4000 &

# 2. تشغيل الوكيل القائد
./opencrabs daemon --host 0.0.0.0 --port 10000
