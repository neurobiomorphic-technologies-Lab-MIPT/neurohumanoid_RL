#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNNER="$ROOT_DIR/experiments/00_official_sim/run_experiment.sh"

for method in aawr awr bc; do
  for seed in 41 42 43; do
    result="$ROOT_DIR/results/stage0/main/$method/$seed/eval.csv"
    if [[ -f "$result" ]]; then
      continue
    fi
    "$RUNNER" "$method" "$seed"
  done
done
