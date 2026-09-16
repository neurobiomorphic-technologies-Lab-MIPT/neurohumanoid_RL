#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SIM_DIR="$ROOT_DIR/.external/so101-simstudio"
SIM_COMMIT="916a0b79abe244e82179e7b0be554cae153ef645"
PATCH="$ROOT_DIR/experiments/01_lerobot_so101/patches/aawr-so101.patch"
PYTHON="$ROOT_DIR/.venv/bin/python"

"$ROOT_DIR/experiments/00_official_sim/bootstrap.sh"

if [[ ! -d "$SIM_DIR/.git" ]]; then
  git clone --filter=blob:none https://github.com/rocPAI-Forge/so101-simstudio.git "$SIM_DIR"
fi
[[ "$(git -C "$SIM_DIR" rev-parse HEAD)" == "$SIM_COMMIT" ]]

if git -C "$ROOT_DIR/.external/aawr" apply --check "$PATCH" 2>/dev/null; then
  git -C "$ROOT_DIR/.external/aawr" apply "$PATCH"
elif ! git -C "$ROOT_DIR/.external/aawr" apply --reverse --check "$PATCH" 2>/dev/null; then
  echo "AAWR source has unexpected SO-101 changes; refusing to continue." >&2
  exit 1
fi

uv pip install --python "$PYTHON" -r "$ROOT_DIR/experiments/01_lerobot_so101/requirements-stage1.txt"
uv pip install --python "$PYTHON" --no-deps -e "$ROOT_DIR/experiments/01_lerobot_so101"

MUJOCO_GL=egl "$PYTHON" "$ROOT_DIR/experiments/01_lerobot_so101/smoke_env.py" \
  --scene "$SIM_DIR/SO101/scenes/simple_pick/scene.xml" --episodes 3
