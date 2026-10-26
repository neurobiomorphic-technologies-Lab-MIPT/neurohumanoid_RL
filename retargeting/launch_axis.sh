#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export XDG_CACHE_HOME="$ROOT/.runtime/cache"
export TMPDIR="$ROOT/.runtime/tmp"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
mkdir -p "$XDG_CACHE_HOME" "$TMPDIR"
cd "$ROOT"
ENV_DIR=".venv-gmr"
for arg in "$@"; do
  if [[ "$arg" == '--backend=pinocchio' || "$arg" == 'pinocchio' ]]; then
    ENV_DIR=".venv-pinocchio"
  fi
done
if [[ ! -x "$ENV_DIR/bin/python" ]]; then
  echo "Missing $ENV_DIR. Run the matching setup script first." >&2
  exit 2
fi
if [[ "${1:-}" == '--demo' ]]; then
  shift
  exec "$ENV_DIR/bin/python" retargeting/axis_studio.py \
    --replay-bvh assets/source/sw2_1_chr01_MAYA.bvh --seconds 60 "$@"
fi
exec "$ENV_DIR/bin/python" retargeting/axis_studio.py --seconds 3600 "$@"
