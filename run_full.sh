#!/bin/bash
cd /home/user/l0084-package
export PYTHONPATH=/home/user/l0084-package/tools
python3 -u -m l0084_entry_mix.cli measure 2>&1
