#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
OUT="${1:-open5e-import-results.md}"
{
  echo "# Archie v2.0.0-alpha.3 Open5e Import Results"
  echo
  echo "Generated: $(date --iso-8601=seconds)"
  echo
  echo "- Archie repo: $PWD"
  echo "- Python: $(python --version 2>&1)"
  echo "- Branch: $(git branch --show-current 2>/dev/null || echo unknown)"
  echo
  echo "## Authorities before import"
  echo '```text'
  python -m archie.cli sources list
  echo '```'
  echo
  echo "## Import srd-2024"
  echo '```text'
  python -m archie.cli sources import open5e srd-2024
  echo '```'
  echo
  echo "## Imported source"
  echo '```text'
  python -m archie.cli sources show open5e:srd-2024
  echo '```'
  echo
  echo "## Authorities after import"
  echo '```text'
  python -m archie.cli sources list
  echo '```'
  echo
  echo "## Database trust-boundary check"
  echo '```text'
  python - <<'PY'
from archie.db import connect
c=connect()
print('enabled sources:', [r[0] for r in c.execute("SELECT id FROM sources WHERE enabled=1 ORDER BY id")])
print('open5e records:', c.execute("SELECT count(*) FROM content_records WHERE source_id='open5e:srd-2024'").fetchone()[0])
print('open5e evidence chunks:', c.execute("SELECT count(*) FROM evidence_chunks WHERE source_id='open5e:srd-2024'").fetchone()[0])
c.close()
PY
  echo '```'
  echo
  echo "Alpha.3 import must leave srd521 as the only enabled authority and Open5e evidence chunks at zero."
} > "$OUT"
echo "Wrote $OUT"
