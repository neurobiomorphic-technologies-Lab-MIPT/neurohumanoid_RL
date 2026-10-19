#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="${GMR_ENV:-$ROOT/.venv-gmr}"

if [[ ! -f "$ROOT/retargeting/GMR/setup.py" ]]; then
  echo "GMR submodule is missing. Run: git submodule update --init --recursive" >&2
  exit 2
fi

python3 -m venv "$ENV_DIR"
"$ENV_DIR/bin/python" -m pip install --upgrade pip
"$ENV_DIR/bin/python" -m pip install -e "$ROOT/retargeting/GMR"

echo "GMR environment: $ENV_DIR"
echo "Run retargeting with: ./retargeting/run.sh"
