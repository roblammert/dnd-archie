#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m archie.cli verify-source
python -m archie.cli ingest
python -m pytest -q
python -m compileall -q archie scripts
python -m archie.cli search "Passive Perception" --top-k 1 >/dev/null
echo "Deterministic release checks PASS"
