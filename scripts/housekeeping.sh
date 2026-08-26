#!/usr/bin/env bash
# One-shot housekeeping: sessions, audit/jobs retention, WAL, orphan uploads,
# leftover restore copies (*.before-restore-*).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-$ROOT}"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi
if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi
"$PY" -c 'from product.housekeeping import run_once; import json; print(json.dumps(run_once(), default=str))'
