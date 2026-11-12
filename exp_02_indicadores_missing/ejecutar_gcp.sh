#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
python run_pipeline.py \
  --data /home/ds/buckets/b1/datasets/competencia_02_crudo.csv.gz \
  --work /home/ds/exp2_marzo_agosto_run01 \
  --remote gs://agustinberna343_buckito2026/exp/exp2_marzo_agosto_run01 \
  --step all
