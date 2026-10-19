#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GMR_DIR="$ROOT/retargeting/GMR"
PYTHON="${GMR_PYTHON:-$ROOT/.venv-gmr/bin/python}"
INPUT="$ROOT/assets/source/sw2_1_chr01_MAYA.bvh"
OUTPUT="$ROOT/assets/retargeted/sw2_1_chr01_MAYA_G1_GMR.pkl"
RECORD_VIDEO=0
RATE_LIMIT=0

usage() {
  printf '%s\n' \
    "Usage: ./retargeting/run.sh [options]" \
    "" \
    "Options:" \
    "  --input PATH       Input Nokov BVH" \
    "  --output PATH      Output GMR pickle" \
    "  --record-video     Record the GMR viewer" \
    "  --rate-limit       Play the viewer at motion speed" \
    "  -h, --help         Show this help"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --record-video) RECORD_VIDEO=1; shift ;;
    --rate-limit) RATE_LIMIT=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ ! -f "$GMR_DIR/scripts/bvh_to_robot.py" ]]; then
  echo "GMR submodule is missing. Run: git submodule update --init --recursive" >&2
  exit 2
fi
if [[ ! -x "$PYTHON" ]]; then
  echo "GMR environment is missing. Run: ./retargeting/setup.sh" >&2
  exit 2
fi
if [[ ! -f "$INPUT" ]]; then
  echo "Input BVH not found: $INPUT" >&2
  exit 2
fi

mkdir -p "$(dirname "$OUTPUT")"
ARGS=(
  --bvh_file "$INPUT"
  --format nokov
  --robot unitree_g1
  --motion_fps 90
  --save_path "$OUTPUT"
)
[[ $RECORD_VIDEO -eq 1 ]] && ARGS+=(--record_video)
[[ $RATE_LIMIT -eq 1 ]] && ARGS+=(--rate_limit)

cd "$GMR_DIR"
exec "$PYTHON" scripts/bvh_to_robot.py "${ARGS[@]}"
