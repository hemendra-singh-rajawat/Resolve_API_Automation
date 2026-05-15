#!/usr/bin/env bash
set -euo pipefail

ENV="${ENV:-dev}"
MARKER="${MARKER:-smoke}"
PARALLEL="${PARALLEL:-4}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# --- venv + deps -------------------------------------------------------------
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# Windows venvs put binaries in Scripts/, POSIX venvs in bin/.
if [[ -d .venv/Scripts ]]; then
  source .venv/Scripts/activate
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

pip install --upgrade pip >/dev/null
pip install -r requirements.txt >/dev/null

# --- pytest ------------------------------------------------------------------
echo "▶ Running [$MARKER] against env=$ENV with $PARALLEL workers"
ENV="$ENV" pytest -n "$PARALLEL" -m "$MARKER" --env "$ENV"

# --- Allure report -----------------------------------------------------------
#
# IMPORTANT: allure-commandline 2.40.0 has broken behaviors-plugin /
# packages-plugin loading on Windows + Java 17/21 — the report builds
# without errors but Behaviors and Packages sidebar tabs come up empty.
# Pin to 2.27.0 or any 2.27.x – 2.34.x release.
#
# Resolution order:
#   1. $ALLURE_BIN override
#   2. ../../node_modules/.bin/allure (sibling npm install on Windows)
#   3. ../../../node_modules/.bin/allure (Desktop/node_modules)
#   4. system PATH
ALLURE=""
if [[ -n "${ALLURE_BIN:-}" && -x "$ALLURE_BIN" ]]; then
  ALLURE="$ALLURE_BIN"
fi
if [[ -z "$ALLURE" ]]; then
  for candidate in \
    "$ROOT/../../node_modules/allure-commandline/dist/bin/allure" \
    "$ROOT/../../../node_modules/allure-commandline/dist/bin/allure" \
    "$ROOT/node_modules/allure-commandline/dist/bin/allure"; do
    if [[ -x "$candidate" ]]; then ALLURE="$candidate"; break; fi
  done
fi
if [[ -z "$ALLURE" ]] && command -v allure >/dev/null 2>&1; then
  ALLURE="$(command -v allure)"
fi

if [[ -n "$ALLURE" ]]; then
  "$ALLURE" generate reports/allure-results -o reports/allure-report --clean
  echo "✔ Allure report: reports/allure-report/index.html"
  echo "  serve with: $ALLURE open reports/allure-report"
else
  echo "⚠ Allure CLI not found — install with: npm install -g allure-commandline@2.27.0"
  echo "  Raw results are at: reports/allure-results"
fi
