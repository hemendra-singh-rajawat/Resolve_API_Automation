#!/usr/bin/env bash
set -euo pipefail

ENV="${ENV:-qa}"
MARKER="${MARKER:-smoke}"
PARALLEL="${PARALLEL:-4}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install --upgrade pip >/dev/null
pip install -r requirements.txt >/dev/null

echo "▶ Running [$MARKER] against env=$ENV with $PARALLEL workers"
ENV="$ENV" pytest -n "$PARALLEL" -m "$MARKER" --env "$ENV"

if command -v allure >/dev/null 2>&1; then
  allure generate reports/allure-results -o reports/allure-report --clean
  echo "✔ Allure report: reports/allure-report/index.html"
else
  echo "⚠ allure CLI not found — raw results at reports/allure-results"
fi
