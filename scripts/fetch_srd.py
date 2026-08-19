from pathlib import Path
import hashlib, json, urllib.request, sys
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'sources/manifest.json').read_text())
out=ROOT/'sources'/m['filename']
with urllib.request.urlopen(m['source_url'],timeout=60) as r:
    data=r.read()
h=hashlib.sha256(data).hexdigest()
if h != m['sha256']:
    print(f"Refusing source: expected {m['sha256']} got {h}",file=sys.stderr); raise SystemExit(2)
out.write_bytes(data)
print(f"Wrote {out} ({len(data)} bytes), SHA-256 verified.")
