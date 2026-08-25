#!/usr/bin/env bash
# Same gates as GitHub Actions CI / test — run locally when Actions is unavailable.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-.}"
if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi
"$PY" tools/check.py
"$PY" -m pytest
