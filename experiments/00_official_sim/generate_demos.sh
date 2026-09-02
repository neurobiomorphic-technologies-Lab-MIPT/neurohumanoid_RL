#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="$ROOT_DIR/data/stage0_xarm_seed41"
GENERATOR="$ROOT_DIR/.external/gym-xarm/generate_demos.py"
PYTHON="$ROOT_DIR/.venv/bin/python"

[[ -x "$PYTHON" ]]
[[ -f "$GENERATOR" ]]
mkdir -p "$OUT_DIR"

if [[ -f "$OUT_DIR/buffer.pkl" ]]; then
  echo "Dataset already exists at $OUT_DIR/buffer.pkl; refusing to overwrite." >&2
  exit 1
fi

cd "$OUT_DIR"
MUJOCO_GL=egl "$PYTHON" -c \
  "import numpy as np; np.random.seed(41); exec(compile(open('$GENERATOR').read(), '$GENERATOR', 'exec'))" \
  > generation.log 2>&1
sha256sum buffer.pkl demos.mp4 > SHA256SUMS
tail -n 16 generation.log
