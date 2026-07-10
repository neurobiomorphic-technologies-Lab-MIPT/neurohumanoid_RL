#!/usr/bin/env bash
set -euo pipefail

cd /home/al/humanoid/dance_sim
exec .venv/bin/python scripts/play_onnx_mjlab.py \
  --motion-file /home/al/humanoid/dance_sim/experiments/full_20p50_to_end.npz \
  --policy /home/al/humanoid/dance_sim/assets/policies/mimic/dance1_subject2/exported/policy.onnx \
  --viewer native \
  --device "${1:-cpu}"
