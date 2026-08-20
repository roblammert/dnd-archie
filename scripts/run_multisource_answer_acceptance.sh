#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

OPEN5E_SOURCE_MANIFEST="sources/open5e/srd-2024/source.yaml"

if [[ ! -f "$OPEN5E_SOURCE_MANIFEST" ]]; then
    echo "ERROR: Open5e source manifest not found: $OPEN5E_SOURCE_MANIFEST" >&2
    exit 1
fi

eval "$(
python - "$OPEN5E_SOURCE_MANIFEST" <<'PY'
from pathlib import Path
import shlex
import sys
import yaml

path = Path(sys.argv[1])
data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

if data.get("approved") is not True:
    raise SystemExit(
        f"ERROR: {path} is not an approved source."
    )

if data.get("enabled") is not True:
    raise SystemExit(
        f"ERROR: {path} is not an enabled source."
    )

name = data.get("license_name")
url = data.get("license_url")

if not name:
    raise SystemExit(
        f"ERROR: {path} does not define license_name."
    )

if not url:
    raise SystemExit(
        f"ERROR: {path} does not define license_url."
    )

print(
    "ARCHIE_OPEN5E_LICENSE_NAME="
    + shlex.quote(str(name))
)
print(
    "ARCHIE_OPEN5E_LICENSE_URL="
    + shlex.quote(str(url))
)
PY
)"

OUT="${1:-open5e-multisource-answer-results.md}"
{
  echo '# Archie v2.0.0-alpha.5 Multi-Source Answer Acceptance Results'
  echo
  echo "Generated: $(date --iso-8601=seconds)"
  echo
  echo '## Branch'
  echo '```text'
  git branch --show-current 2>/dev/null || true
  echo '```'
  echo
  echo '## Prepare approved Open5e SRD source'
  echo '```text'
  python -m archie.cli sources discover open5e
  python -m archie.cli sources import open5e srd-2024
  python -m archie.cli sources approve open5e:srd-2024 \
    --license-name "$ARCHIE_OPEN5E_LICENSE_NAME" \
    --license-url "$ARCHIE_OPEN5E_LICENSE_URL" \
    --note 'alpha.5 live acceptance explicit approval'
  python -m archie.cli sources enable open5e:srd-2024
  python -m archie.cli sources verify
  echo '```'
  echo
  echo '## Source state'
  echo '```text'
  python -m archie.cli sources list
  echo '```'
  echo
  echo '## Answer 1 — canonical rules question'
  echo '**Question:** What happens when I have Advantage on a roll?'
  echo '```text'
  python -m archie.cli ask 'What happens when I have Advantage on a roll?'
  echo '```'
  echo
  echo '## Answer 2 — structured spell question'
  echo '**Question:** Which classes can cast Fireball?'
  echo '```text'
  python -m archie.cli ask 'Which classes can cast Fireball?'
  echo '```'
  echo
  echo '## Answer 3 — structured item question'
  echo '**Question:** Does a Wand of Fireballs require attunement?'
  echo '```text'
  python -m archie.cli ask 'Does a Wand of Fireballs require attunement?'
  echo '```'
  echo
  echo '## Retrieval profile — Fireball'
  echo '```text'
  python -m archie.cli search 'Fireball' --top-k 10
  echo '```'
  echo
  echo '## Conflict report'
  echo '```text'
  python -m archie.cli sources conflicts | head -100
  echo '```'
} > "$OUT"

echo "Wrote $OUT"
