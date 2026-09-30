#!/bin/bash
# 1. تشغيل الموزع الذكي في الخلفية
litellm --config litellm_config.yaml --port 4000 &

# 2. تشغيل الوكيل القائد 
./opencrabs daemon
