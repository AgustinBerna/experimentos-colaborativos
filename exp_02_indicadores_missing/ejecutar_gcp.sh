#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
PYTHON_BIN="${EXP2_PYTHON:-python}"
DATA="${EXP2_DATA:-/home/ds/buckets/b1/datasets/competencia_02_crudo.csv.gz}"
WORK="${EXP2_WORK:-/home/ds/exp2_indicadores_lags_deltas_optuna_run01}"
REMOTE="${EXP2_REMOTE:-gs://agustinberna343_buckito2026/exp/exp2_indicadores_lags_deltas_optuna_run01}"
STEP="${EXP2_STEP:-all}"
if [[ ! -f "$DATA" ]]; then
  echo "No existe el dataset: $DATA. Configurar EXP2_DATA." >&2
  exit 1
fi
"$PYTHON_BIN" -m unittest discover -s tests -v
"$PYTHON_BIN" run_pipeline.py --data "$DATA" --work "$WORK" --remote "$REMOTE" --step "$STEP"
