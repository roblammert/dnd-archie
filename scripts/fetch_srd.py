from pathlib import Path
import hashlib, urllib.request, sys, yaml
ROOT=Path(__file__).resolve().parents[1]
manifest_path=ROOT/'sources'/'srd521'/'source.yaml'
m=yaml.safe_load(manifest_path.read_text(encoding='utf-8'))
v=m['version']
out=manifest_path.parent/v['filename']
with urllib.request.urlopen(v['source_uri'],timeout=60) as r:
    data=r.read()
h=hashlib.sha256(data).hexdigest()
if h != v['sha256']:
    print(f"Refusing source: expected {v['sha256']} got {h}",file=sys.stderr); raise SystemExit(2)
out.write_bytes(data)
print(f"Wrote {out} ({len(data)} bytes), SHA-256 verified.")
