#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${E7_PYTHON:-python3}"
if [ ! -x .venv/bin/python ]; then "$PYTHON" -m venv .venv; fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
export OMP_NUM_THREADS=7
exec .venv/bin/python correr_e7.py "$@"
