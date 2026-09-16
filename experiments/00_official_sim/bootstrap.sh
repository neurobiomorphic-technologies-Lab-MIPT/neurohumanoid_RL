#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AAWR_DIR="$ROOT_DIR/.external/aawr"
XARM_DIR="$ROOT_DIR/.external/gym-xarm"
VENV_DIR="$ROOT_DIR/.venv"
AAWR_REV="05845db6c0da25993e816c44f47c123487f20cd1"
XARM_REV="388227ab683516d014bb7273350ac78c10faf84b"
LOGGING_PATCH="$ROOT_DIR/experiments/00_official_sim/patches/aawr-local-logging.patch"
BC_ONLINE_PATCH="$ROOT_DIR/experiments/00_official_sim/patches/aawr-bc-online.patch"
REQ_FILE="$ROOT_DIR/experiments/00_official_sim/requirements-stage0.txt"

mkdir -p "$ROOT_DIR/.external"

if [[ ! -d "$AAWR_DIR/.git" ]]; then
  git clone --quiet https://github.com/penn-pal-lab/aawr.git "$AAWR_DIR"
  git -C "$AAWR_DIR" checkout --quiet --detach "$AAWR_REV"
fi

if [[ ! -d "$XARM_DIR/.git" ]]; then
  git clone --quiet https://github.com/edwhu/gym-xarm.git "$XARM_DIR"
  git -C "$XARM_DIR" checkout --quiet --detach "$XARM_REV"
fi

[[ "$(git -C "$AAWR_DIR" rev-parse HEAD)" == "$AAWR_REV" ]]
[[ "$(git -C "$XARM_DIR" rev-parse HEAD)" == "$XARM_REV" ]]
git -C "$XARM_DIR" diff --quiet

for patch_file in "$LOGGING_PATCH" "$BC_ONLINE_PATCH"; do
  apply_args=()
  if [[ "$patch_file" == "$BC_ONLINE_PATCH" ]]; then
    apply_args+=(--unidiff-zero)
  fi
  if git -C "$AAWR_DIR" apply "${apply_args[@]}" --check "$patch_file" 2>/dev/null; then
    git -C "$AAWR_DIR" apply "${apply_args[@]}" "$patch_file"
  elif ! git -C "$AAWR_DIR" apply "${apply_args[@]}" --reverse --check "$patch_file" 2>/dev/null; then
    echo "AAWR worktree has unexpected changes; refusing to apply $patch_file." >&2
    exit 1
  fi
done

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  uv venv --python 3.11 "$VENV_DIR"
fi

uv pip install --python "$VENV_DIR/bin/python" \
  --index https://download.pytorch.org/whl/cu128 'torch==2.10.0'
uv pip install --python "$VENV_DIR/bin/python" -r "$REQ_FILE"
uv pip install --python "$VENV_DIR/bin/python" --no-deps -e "$XARM_DIR"

MUJOCO_GL=egl "$VENV_DIR/bin/python" - <<'PY'
import gymnasium as gym
import gym_xarm  # noqa: F401
import numpy as np
import torch

assert torch.cuda.is_available(), "CUDA is required by the upstream AWR baseline"
env = gym.make("gym_xarm/PrivilegedXarmLift-v0", render_mode="rgb_array")
obs, _ = env.reset(seed=41)
obs, _, _, _, _ = env.step(np.zeros(4, dtype=np.float32))
frame = env.render()
assert obs["rgb"].shape == (84, 84, 3)
assert obs["state"].shape == (7,)
assert frame.shape == (256, 256, 3)
env.close()
print("Stage 0 environment smoke test passed.")
PY
