#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="${PINOCCHIO_ENV:-$ROOT/.venv-pinocchio}"

if ! command -v conda >/dev/null; then
  echo 'Conda is required because pip Pinocchio wheels omit pinocchio.casadi.' >&2
  exit 2
fi
if [[ ! -x "$ENV_DIR/bin/python" ]]; then
  conda create -y -p "$ENV_DIR" -c conda-forge \
    python=3.11 pinocchio=3.1.0 casadi=3.6.7 numpy=1.26 scipy
fi
if ! "$ENV_DIR/bin/python" -c 'from pinocchio import casadi' 2>/dev/null; then
  echo "$ENV_DIR is not a conda Pinocchio environment with CasADi bindings." >&2
  exit 2
fi
"$ENV_DIR/bin/python" -m pip install \
  mujoco mink loop_rate_limiters 'qpsolvers[proxqp]' rich tqdm natsort imageio
"$ENV_DIR/bin/python" -m pip install --no-deps -e "$ROOT/retargeting/GMR"

echo "Pinocchio environment: $ENV_DIR"
echo "Run: $ENV_DIR/bin/python retargeting/axis_studio.py --backend pinocchio --mode full-body"
