#!/usr/bin/env bash
# Reproducible deploy for the automation-agent template (Linux/macOS/Git-Bash).
# Installs dependencies, validates the project pack, and runs a smoke test.
#
#   scripts/deploy.sh            # full deploy with validation
#   scripts/deploy.sh --skip-tests   # skip the pytest smoke test
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SKIP_TESTS=0
for arg in "$@"; do
  [ "$arg" = "--skip-tests" ] && SKIP_TESTS=1
done

echo "==> 1/4 Python-Version"
python --version

echo "==> 2/4 Abhängigkeiten installieren"
python -m pip install -q -r requirements.txt
[ -f requirements-dev.txt ] && python -m pip install -q -r requirements-dev.txt

echo "==> 3/4 Projekt-Pack validieren (tools/check.py)"
# Fail the deploy on any manifest/config error. Not skippable — the gate is the point.
python tools/check.py

if [ "$SKIP_TESTS" -eq 0 ]; then
  echo "==> 4/4 Smoke-Test (pytest)"
  python -m pytest -q
else
  echo "==> 4/4 Smoke-Test übersprungen (--skip-tests)"
fi

echo "✓ Deploy-Prüfung abgeschlossen. Start mit: python agent.py"
