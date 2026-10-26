#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${GMR_PYTHON:-$ROOT/.venv-gmr/bin/python}"
SDK_ROOT="$ROOT/.deps/axis-studio-reference"
if [[ ! -x "$PYTHON" ]]; then
  echo 'Run ./retargeting/setup.sh first, or set GMR_PYTHON.' >&2
  exit 2
fi
if [[ $# -gt 0 ]]; then
  # Install an existing MocapApi distribution containing setup.py.
  "$PYTHON" -m pip install "$1"
else
  mkdir -p "$ROOT/.deps"
  if [[ ! -d "$SDK_ROOT/.git" ]]; then
    git clone --filter=blob:none --no-checkout \
      https://github.com/RomanSentsov/unitree-g1-axis-studio-retarget.git "$SDK_ROOT"
  fi
  git -C "$SDK_ROOT" sparse-checkout set MocapApi/MocapApi
  git -C "$SDK_ROOT" checkout be0a8e0d713697acce94e8b97c49009bc47a3452
  "$PYTHON" -m pip install --no-build-isolation --no-deps "$SDK_ROOT/MocapApi/MocapApi"
fi
"$PYTHON" -c 'from mocap_api import MCPApplication; print("MocapApi import OK")'
