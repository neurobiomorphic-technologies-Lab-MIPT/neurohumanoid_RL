#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REFERENCE_DIR="$ROOT_DIR/data/so101_simstudio_reference"
REFERENCE="$REFERENCE_DIR/data/chunk-000/file-000.parquet"
OUTPUT="$ROOT_DIR/data/stage1_so101_lift"
REVISION="cfd2210d0bcd824f07cf38efcbf117c0569458c5"
URL="https://huggingface.co/datasets/alexhegit/so101-simstudio-lab01-pnp/resolve/$REVISION/data/chunk-000/file-000.parquet"

mkdir -p "$(dirname "$REFERENCE")" "$OUTPUT"
if [[ ! -f "$REFERENCE" ]]; then
  curl --fail --location --retry 3 --connect-timeout 10 --max-time 180 "$URL" -o "$REFERENCE"
fi
echo "96187202de3e838b818e46ce8c8ac15a7623e90b97ad03e70ca7461e2e317e21605  $REFERENCE" | sha256sum --check --status

if [[ -e "$OUTPUT/buffer.pkl" || -e "$OUTPUT/reset_profiles.npz" ]]; then
  echo "Dataset already exists under $OUTPUT; refusing to overwrite." >&2
  exit 1
fi

MUJOCO_GL=egl "$ROOT_DIR/.venv/bin/python" \
  "$ROOT_DIR/experiments/01_lerobot_so101/build_demos.py" \
  --reference "$REFERENCE" \
  --scene "$ROOT_DIR/.external/so101-simstudio/SO101/scenes/simple_pick/scene.xml" \
  --output "$OUTPUT" \
  --repeats 4
