from __future__ import annotations
import hashlib, json
from .config import settings

class SourceIntegrityError(RuntimeError):
    pass

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def load_manifest():
    return json.loads(settings.manifest.read_text(encoding='utf-8'))

def verify_source() -> dict:
    m=load_manifest()
    if not settings.source_pdf.exists():
        raise SourceIntegrityError(f"Missing approved source: {settings.source_pdf}")
    actual=sha256_file(settings.source_pdf)
    expected=m['sha256']
    if actual != expected:
        raise SourceIntegrityError(f"SRD SHA-256 mismatch. expected={expected} actual={actual}")
    return {"ok":True,"authority_id":m['authority_id'],"sha256":actual,"file":str(settings.source_pdf)}
