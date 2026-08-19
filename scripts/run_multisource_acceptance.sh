#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

: "${ARCHIE_OPEN5E_LICENSE_NAME:?Set ARCHIE_OPEN5E_LICENSE_NAME after independently verifying the imported source license.}"
: "${ARCHIE_OPEN5E_LICENSE_URL:?Set ARCHIE_OPEN5E_LICENSE_URL after independently verifying the imported source license URL.}"

OUT="${1:-open5e-multisource-results.md}"
{
  echo '# Archie v2.0.0-alpha.4 Multi-Source Acceptance Results'
  echo
  echo "Generated: $(date --iso-8601=seconds)"
  echo
  echo '## Branch'
  echo '```text'
  git branch --show-current 2>/dev/null || true
  echo '```'
  echo
  echo '## Sources before'
  echo '```text'
  python -m archie.cli sources list
  echo '```'
  echo
  echo '## Discovery + import'
  echo '```text'
  python -m archie.cli sources discover open5e
  python -m archie.cli sources import open5e srd-2024
  echo '```'
  echo
  echo '## Explicit approval + enablement'
  echo '```text'
  python -m archie.cli sources approve open5e:srd-2024 --license-name "$ARCHIE_OPEN5E_LICENSE_NAME" --license-url "$ARCHIE_OPEN5E_LICENSE_URL" --note 'alpha.4 live acceptance explicit approval'
  python -m archie.cli sources enable open5e:srd-2024
  python -m archie.cli sources verify
  echo '```'
  echo
  echo '## Enabled source state'
  echo '```text'
  python -m archie.cli sources show open5e:srd-2024
  echo '```'
  echo
  echo '## Database trust check'
  echo '```text'
  python - <<'PY'
from archie.db import connect
c=connect()
print('enabled sources:', [r[0] for r in c.execute("SELECT id FROM sources WHERE enabled=1 ORDER BY priority DESC,id")])
print('open5e records:', c.execute("SELECT count(*) FROM content_records WHERE source_id='open5e:srd-2024'").fetchone()[0])
print('open5e evidence chunks:', c.execute("SELECT count(*) FROM evidence_chunks WHERE source_id='open5e:srd-2024'").fetchone()[0])
print('2014 enabled evidence:', c.execute("SELECT count(*) FROM evidence_chunks e JOIN sources s ON s.id=e.source_id WHERE s.enabled=1 AND s.edition='2014'").fetchone()[0])
c.close()
PY
  echo '```'
  echo
  echo '## Retrieval sample'
  echo '```text'
  python -m archie.cli search 'Fireball' --top-k 8
  echo '```'
  echo
  echo '## Structured overlap report'
  echo '```text'
  python -m archie.cli sources conflicts | head -100
  echo '```'
} > "$OUT"
echo "Wrote $OUT"
