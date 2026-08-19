#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

OUTPUT="${1:-open5e-discovery-results.md}"
TMP_JSON="$(mktemp)"
trap 'rm -f "$TMP_JSON"' EXIT

{
  echo "# Archie v2.0.0-alpha.2 Open5e Discovery Results"
  echo
  echo "Generated: $(date --iso-8601=seconds)"
  echo
  echo "- Archie repo: $PWD"
  echo "- Python: $(python --version 2>&1)"
  echo "- Branch: $(git branch --show-current 2>/dev/null || echo unknown)"
  echo
  echo "## Local authorities before discovery"
  echo
  echo '```text'
  python -m archie.cli sources list
  echo '```'
  echo
} > "$OUTPUT"

python -m archie.cli sources discover open5e --json > "$TMP_JSON"

python - "$TMP_JSON" >> "$OUTPUT" <<'PY'
import json, sys
p=sys.argv[1]
d=json.load(open(p))
print("## Open5e discovery summary\n")
print(f"- API version: {d.get('api_version')}")
print(f"- Base URL: {d.get('base_url')}")
print(f"- Documents discovered: {d.get('document_count')}")
print(f"- Snapshot: {d.get('snapshot_path')}")
print(f"- Snapshot SHA-256: `{d.get('snapshot_sha256')}`")
print(f"- Imported into Archie: {d.get('imported_into_archie')}\n")
print("## Document inventory\n")
for doc in d.get('documents', []):
    lic=doc.get('license')
    pub=doc.get('publisher')
    def label(v):
        if isinstance(v,dict): return v.get('name') or v.get('key') or '-'
        return v or '-'
    counts=doc.get('resource_counts') or {}
    total=sum(v for v in counts.values() if isinstance(v,int))
    print(f"### {doc.get('key')} — {doc.get('name')}\n")
    print(f"- Publisher: {label(pub)}")
    print(f"- License: {label(lic)}")
    print(f"- Type: {doc.get('document_type') or '-'}")
    print(f"- Game system: {label(doc.get('game_system'))}")
    print(f"- Resources counted: {total}")
    print("- Counts: " + ", ".join(f"{k}={v if v is not None else '?'}" for k,v in counts.items()))
    if doc.get('permalink'): print(f"- Permalink: {doc['permalink']}")
    print()
PY

{
  echo "## Local authorities after discovery"
  echo
  echo '```text'
  python -m archie.cli sources list
  echo '```'
  echo
  echo "Discovery is inventory-only; the before/after authority list should be unchanged."
} >> "$OUTPUT"

echo "Open5e discovery report written to: $OUTPUT"
