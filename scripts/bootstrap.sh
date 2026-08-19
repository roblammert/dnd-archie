#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m archie.cli verify-source
python -m archie.cli ingest
printf '\nArchie v1.5.1 bootstrap complete.\n'
printf 'Review .env and set your local LLM endpoint if needed.\n'
printf 'Try: python -m archie.cli diagnose-retrieval "What does Prone do?"\n'
