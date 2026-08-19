#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m archie.cli verify-source
python -m archie.cli ingest
printf '\nArchie bootstrap complete.\nTry: source .venv/bin/activate && python -m archie.cli search "advantage"\n'
