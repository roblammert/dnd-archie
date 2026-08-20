#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
python -m archie.cli sources verify
python -m archie.cli ingest
python -m pytest -q
python -m compileall -q archie scripts
python -m archie.cli search "Passive Perception" --top-k 1 >/dev/null
python -m archie.cli diagnose-retrieval "What does Prone do?" --top-k 3 >/dev/null
python -m archie.cli sources list >/dev/null
python -m archie.cli sources show srd521 >/dev/null
# Live Open5e discovery/import remain explicit network acceptance tests.
echo "Archie v2.0.0-alpha.6.1 deterministic release checks PASS"
