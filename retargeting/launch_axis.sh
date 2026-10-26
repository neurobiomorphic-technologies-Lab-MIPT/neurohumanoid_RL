#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export XDG_CACHE_HOME="$ROOT/.runtime/cache"
export TMPDIR="$ROOT/.runtime/tmp"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
mkdir -p "$XDG_CACHE_HOME" "$TMPDIR"
cd "$ROOT"
if [[ ! -x .venv-gmr/bin/python ]]; then
  echo 'Run ./retargeting/setup.sh and ./retargeting/setup_axis.sh first.' >&2
  exit 2
fi
if [[ "${1:-}" == '--demo' ]]; then
  shift
  exec .venv-gmr/bin/python retargeting/axis_studio.py \
    --replay-bvh assets/source/sw2_1_chr01_MAYA.bvh --seconds 60 "$@"
fi
exec .venv-gmr/bin/python retargeting/axis_studio.py --seconds 3600 "$@"
