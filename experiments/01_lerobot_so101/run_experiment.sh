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
DATASET="$ROOT_DIR/data/stage1_so101_lift"
OFFLINE_STEPS="${OFFLINE_STEPS:-20000}"
TRAIN_STEPS="${TRAIN_STEPS:-40000}"
EVAL_EPISODES="${EVAL_EPISODES:-20}"
SAVE_VIDEO="${SAVE_VIDEO:-true}"
SAVE_MODEL="${SAVE_MODEL:-true}"
RESULT="$ROOT_DIR/results/stage1/runs/$METHOD/$SEED/steps_$TRAIN_STEPS"

case "$METHOD" in
  bc) AGENT=bc; MODALITY=pixels ;;
  awr) AGENT=awr; MODALITY=pixels ;;
  aawr) AGENT=asym_awr; MODALITY=all ;;
  *) echo "Unknown method: $METHOD" >&2; exit 2 ;;
esac

[[ -f "$DATASET/buffer.pkl" ]]
[[ -f "$DATASET/reset_profiles.npz" ]]
mkdir -p "$RESULT"
if [[ -f "$RESULT/eval.csv" ]]; then
  echo "Completed result already exists at $RESULT/eval.csv; refusing to rerun." >&2
  exit 1
fi

EXP_NAME="stage1_so101_${METHOD}_${TRAIN_STEPS}"
UPSTREAM_LOG="$AAWR_DIR/logs/gymnasium_so101_lift/$MODALITY/$EXP_NAME/$SEED"
CONSOLE_LOG="$RESULT/console.log"

cd "$AAWR_DIR"
if ! SO101_SCENE_PATH="$ROOT_DIR/.external/so101-simstudio/SO101/scenes/simple_pick/scene.xml" \
  SO101_RESET_PROFILES="$DATASET/reset_profiles.npz" \
  MUJOCO_GL=egl WANDB_MODE=disabled PYTHONUNBUFFERED=1 PYTHONPATH=src \
  "$ROOT_DIR/.venv/bin/python" src/train_il.py \
  agent="$AGENT" modality="$MODALITY" task=gymnasium_so101_lift \
  dataset_dir="$DATASET" seed="$SEED" use_wandb=false exp_name="$EXP_NAME" \
  horizon=1 offline_steps="$OFFLINE_STEPS" train_steps="$TRAIN_STEPS" \
  lr=1e-4 grad_clip_norm=10 awr_filter=indicator expectile=0.9 A_scaling=3 \
  save_video="$SAVE_VIDEO" save_model="$SAVE_MODEL" switch_awr_filter=true \
  eval_episodes="$EVAL_EPISODES" > "$CONSOLE_LOG" 2>&1; then
  tail -n 100 "$CONSOLE_LOG" >&2
  exit 1
fi

cp "$UPSTREAM_LOG/eval.log" "$RESULT/eval.csv"
cp "$UPSTREAM_LOG/config.yaml" "$RESULT/config.yaml"
if [[ "$SAVE_MODEL" == true ]]; then
  cp -a "$UPSTREAM_LOG/models" "$RESULT/models"
fi
tail -n 24 "$CONSOLE_LOG"
