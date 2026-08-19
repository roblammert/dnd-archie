from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import yaml
from .config import settings

class SourceIntegrityError(RuntimeError):
    pass

@dataclass(frozen=True)
class SourceManifest:
    id: str
    name: str
    source_type: str
    authority_type: str
    edition: str | None
    enabled: bool
    approved: bool
    license_status: str
    provider: str | None
    provider_document_key: str | None
    priority: int
    license_name: str | None
    license_url: str | None
    homepage_url: str | None
    version: str
    filename: str
    sha256: str
    source_uri: str | None
    manifest_path: Path

    @property
    def content_path(self) -> Path:
        return self.manifest_path.parent / self.filename

    def to_dict(self):
        d = asdict(self)
        d['manifest_path'] = str(self.manifest_path)
        d['content_path'] = str(self.content_path)
        return d

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise SourceIntegrityError(f"Invalid source manifest: {path}")
    return data

def load_source_manifest(path: Path) -> SourceManifest:
    data = _load_yaml(path)
    ver = data.get('version') or {}
    required = ('id','name','source_type','authority_type')
    missing = [x for x in required if not data.get(x)]
    for x in ('version','filename','sha256'):
        if not ver.get(x): missing.append(f'version.{x}')
    if missing:
        raise SourceIntegrityError(f"Source manifest {path} missing: {', '.join(missing)}")
    return SourceManifest(
        id=str(data['id']), name=str(data['name']), source_type=str(data['source_type']),
        authority_type=str(data['authority_type']), edition=str(data['edition']) if data.get('edition') is not None else None,
        enabled=bool(data.get('enabled', True)), approved=bool(data.get('approved', data.get('enabled', True))),
        license_status=str(data.get('license_status') or ('present' if data.get('license_name') else 'missing')),
        provider=data.get('provider'), provider_document_key=data.get('provider_document_key'),
        priority=int(data.get('priority',100)), license_name=data.get('license_name'), license_url=data.get('license_url'),
        homepage_url=data.get('homepage_url'), version=str(ver['version']), filename=str(ver['filename']),
        sha256=str(ver['sha256']).lower(), source_uri=ver.get('source_uri'), manifest_path=path,
    )

def discover_source_manifests() -> list[SourceManifest]:
    if not settings.sources_dir.exists(): return []
    return [load_source_manifest(path) for path in sorted(settings.sources_dir.rglob('source.yaml'))]

def get_source_manifest(source_id: str) -> SourceManifest:
    for manifest in discover_source_manifests():
        if manifest.id == source_id: return manifest
    raise SourceIntegrityError(f"Unknown source: {source_id}")

def load_manifest():
    m = get_source_manifest(settings.source_id)
    return {'schema_version':3,'authority_id':m.id,'title':m.name,'filename':m.filename,'sha256':m.sha256,
            'source_url':m.source_uri,'license':m.license_name,'authoritative':m.authority_type=='official_srd',
            'source_type':m.source_type,'authority_type':m.authority_type,'edition':m.edition,'enabled':m.enabled,
            'approved':m.approved,'priority':m.priority}

def verify_manifest(manifest: SourceManifest) -> dict:
    path=manifest.content_path
    if not path.exists(): raise SourceIntegrityError(f"Missing approved source: {path}")
    actual=sha256_file(path)
    if actual != manifest.sha256:
        raise SourceIntegrityError(f"Source SHA-256 mismatch for {manifest.id}. expected={manifest.sha256} actual={actual}")
    return {'ok':True,'source_id':manifest.id,'authority_id':manifest.id,'name':manifest.name,
            'authority_type':manifest.authority_type,'edition':manifest.edition,'version':manifest.version,
            'sha256':actual,'file':str(path),'enabled':manifest.enabled,'approved':manifest.approved,
            'license_status':manifest.license_status}

def verify_source() -> dict:
    return verify_manifest(get_source_manifest(settings.source_id))

def verify_enabled_sources() -> list[dict]:
    results=[]
    for manifest in discover_source_manifests():
        if manifest.enabled:
            if not manifest.approved:
                raise SourceIntegrityError(f"Enabled source is not approved: {manifest.id}")
            if manifest.license_status != 'present':
                raise SourceIntegrityError(f"Enabled source lacks verified license metadata: {manifest.id}")
            results.append(verify_manifest(manifest))
    return results
