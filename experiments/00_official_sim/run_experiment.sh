#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 {bc|awr|aawr} SEED" >&2
  exit 2
fi

METHOD="$1"
SEED="$2"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AAWR_DIR="$ROOT_DIR/.external/aawr"
PYTHON="$ROOT_DIR/.venv/bin/python"
DATASET_DIR="$ROOT_DIR/data/stage0_xarm_seed41"
RESULT_DIR="$ROOT_DIR/results/stage0/main/$METHOD/$SEED"
OFFLINE_STEPS="${OFFLINE_STEPS:-20000}"
TRAIN_STEPS="${TRAIN_STEPS:-40000}"
SAVE_VIDEO="${SAVE_VIDEO:-true}"

case "$METHOD" in
  bc)
    AGENT="bc"
    MODALITY="pixels"
    ;;
  awr)
    AGENT="awr"
    MODALITY="pixels"
    ;;
  aawr)
    AGENT="asym_awr"
    MODALITY="all"
    ;;
  *)
    echo "Unknown method: $METHOD" >&2
    exit 2
    ;;
esac

[[ -x "$PYTHON" ]]
[[ -f "$DATASET_DIR/buffer.pkl" ]]
mkdir -p "$RESULT_DIR"

if [[ -f "$RESULT_DIR/eval.csv" ]]; then
  echo "Completed result already exists at $RESULT_DIR/eval.csv; refusing to rerun." >&2
  exit 1
fi

EXP_NAME="stage0_main_${METHOD}"
UPSTREAM_LOG_DIR="$AAWR_DIR/logs/gymnasium_xarm_lift/$MODALITY/$EXP_NAME/$SEED"
CONSOLE_LOG="$RESULT_DIR/console.log"

cd "$AAWR_DIR"
if ! MUJOCO_GL=egl WANDB_MODE=disabled PYTHONUNBUFFERED=1 PYTHONPATH=src "$PYTHON" src/train_il.py \
  agent="$AGENT" \
  modality="$MODALITY" \
  task=gymnasium_xarm_lift \
  dataset_dir="$DATASET_DIR" \
  seed="$SEED" \
  use_wandb=false \
  exp_name="$EXP_NAME" \
  horizon=1 \
  offline_steps="$OFFLINE_STEPS" \
  train_steps="$TRAIN_STEPS" \
  lr=1e-4 \
  grad_clip_norm=10 \
  awr_filter=indicator \
  expectile=0.9 \
  A_scaling=3 \
  save_video="$SAVE_VIDEO" \
  save_model=false \
  switch_awr_filter=true \
  > "$CONSOLE_LOG" 2>&1; then
  tail -n 100 "$CONSOLE_LOG" >&2
  exit 1
fi

cp "$UPSTREAM_LOG_DIR/eval.log" "$RESULT_DIR/eval.csv"
cp "$UPSTREAM_LOG_DIR/config.yaml" "$RESULT_DIR/config.yaml"
tail -n 24 "$CONSOLE_LOG"
