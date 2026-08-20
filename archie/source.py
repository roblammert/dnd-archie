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
    authority_id: str | None
    representation_id: str | None
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
    upstream_revision: str | None
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
        authority_id=str(data['authority_id']) if data.get('authority_id') is not None else None,
        representation_id=str(data['representation_id']) if data.get('representation_id') is not None else None,
        enabled=bool(data.get('enabled', True)), approved=bool(data.get('approved', data.get('enabled', True))),
        license_status=str(data.get('license_status') or ('present' if data.get('license_name') else 'missing')),
        provider=data.get('provider'), provider_document_key=data.get('provider_document_key'),
        priority=int(data.get('priority',100)), license_name=data.get('license_name'), license_url=data.get('license_url'),
        homepage_url=data.get('homepage_url'), version=str(ver['version']), filename=str(ver['filename']),
        sha256=str(ver['sha256']).lower(), source_uri=ver.get('source_uri'),
        upstream_revision=str(ver['upstream_revision']) if ver.get('upstream_revision') is not None else None,
        manifest_path=path,
    )

def load_authority_declaration(path: Path | None = None) -> dict[str, dict[str, str]]:
    path = path or settings.sources_dir / 'wotc-srd-5.2.1.yaml'
    data = _load_yaml(path)
    schema_version = data.get('schema_version')
    if type(schema_version) is not int or schema_version != 1:
        raise SourceIntegrityError(
            f"Authority declaration {path} has unsupported schema_version: {schema_version!r}; expected 1"
        )
    authority = data.get('authority')
    representations = data.get('representations')
    authority_id = authority.get('id') if isinstance(authority, dict) else None
    if not isinstance(authority_id, str) or not authority_id.strip():
        raise SourceIntegrityError(f"Authority declaration {path} lacks authority.id")
    if not isinstance(representations, list):
        raise SourceIntegrityError(f"Authority declaration {path} lacks representations")
    representation_sources: dict[str, str] = {}
    for item in representations:
        representation_id = item.get('id') if isinstance(item, dict) else None
        source_id = item.get('source_id') if isinstance(item, dict) else None
        if not isinstance(representation_id, str) or not representation_id.strip():
            raise SourceIntegrityError(f"Authority declaration {path} has malformed representation metadata")
        if not isinstance(source_id, str) or not source_id.strip():
            raise SourceIntegrityError(f"Authority declaration {path} lacks source binding for {representation_id}")
        if representation_id in representation_sources:
            raise SourceIntegrityError(f"Authority declaration {path} repeats representation: {representation_id}")
        if source_id in representation_sources.values():
            raise SourceIntegrityError(f"Authority declaration {path} repeats source binding: {source_id}")
        representation_sources[representation_id] = source_id
    if not representation_sources:
        raise SourceIntegrityError(f"Authority declaration {path} declares no representations")
    return {authority_id: representation_sources}

def validate_manifest_authority(manifest: SourceManifest) -> None:
    declarations = load_authority_declaration()
    if not manifest.authority_id:
        raise SourceIntegrityError(f"Source manifest {manifest.manifest_path} lacks authority_id")
    if manifest.authority_id not in declarations:
        raise SourceIntegrityError(f"Unknown authority_id for {manifest.id}: {manifest.authority_id}")
    if not manifest.representation_id:
        raise SourceIntegrityError(f"Source manifest {manifest.manifest_path} lacks representation_id")
    if manifest.representation_id not in declarations[manifest.authority_id]:
        raise SourceIntegrityError(
            f"Representation {manifest.representation_id} is not declared for authority {manifest.authority_id}"
        )
    expected_source_id = declarations[manifest.authority_id][manifest.representation_id]
    if manifest.id != expected_source_id:
        raise SourceIntegrityError(
            f"Source {manifest.id} cannot claim representation {manifest.representation_id}; "
            f"expected source {expected_source_id}"
        )

def validate_content_authority(c) -> dict:
    declarations = load_authority_declaration()
    allowed = {(authority_id, representation_id): source_id
               for authority_id, representations in declarations.items()
               for representation_id, source_id in representations.items()}
    rows = c.execute(
        '''SELECT cr.id,cr.source_id,cr.authority_id,cr.representation_id,
                  s.authority_id AS source_authority_id,s.representation_id AS source_representation_id
           FROM content_records cr JOIN sources s ON s.id=cr.source_id'''
    ).fetchall()
    observed_authorities: set[str] = set()
    observed_representations: set[str] = set()
    for row in rows:
        pair = (row['authority_id'], row['representation_id'])
        if pair not in allowed:
            raise SourceIntegrityError(
                f"Content record {row['id']} from {row['source_id']} has undeclared authority/representation: "
                f"{row['authority_id']}/{row['representation_id']}"
            )
        if row['source_id'] != allowed[pair]:
            raise SourceIntegrityError(
                f"Content record {row['id']} uses representation {row['representation_id']} "
                f"through invalid source {row['source_id']}"
            )
        if pair != (row['source_authority_id'], row['source_representation_id']):
            raise SourceIntegrityError(
                f"Content record {row['id']} provenance does not match source {row['source_id']}"
            )
        observed_authorities.add(row['authority_id'])
        observed_representations.add(row['representation_id'])
    return {'content_records': len(rows), 'authority_ids': sorted(observed_authorities),
            'representation_ids': sorted(observed_representations)}

def discover_source_manifests() -> list[SourceManifest]:
    if not settings.sources_dir.exists(): return []
    return [load_source_manifest(path) for path in sorted(settings.sources_dir.rglob('source.yaml'))]

def get_source_manifest(source_id: str) -> SourceManifest:
    for manifest in discover_source_manifests():
        if manifest.id == source_id: return manifest
    raise SourceIntegrityError(f"Unknown source: {source_id}")

def load_manifest():
    m = get_source_manifest(settings.source_id)
    return {'schema_version':3,'authority_id':m.authority_id or m.id,'representation_id':m.representation_id,
            'title':m.name,'filename':m.filename,'sha256':m.sha256,
            'source_url':m.source_uri,'license':m.license_name,'authoritative':m.authority_type=='official_srd',
            'source_type':m.source_type,'authority_type':m.authority_type,'edition':m.edition,'enabled':m.enabled,
            'approved':m.approved,'priority':m.priority}

def verify_manifest(manifest: SourceManifest) -> dict:
    validate_manifest_authority(manifest)
    path=manifest.content_path
    if not path.exists(): raise SourceIntegrityError(f"Missing approved source: {path}")
    actual=sha256_file(path)
    if actual != manifest.sha256:
        raise SourceIntegrityError(f"Source SHA-256 mismatch for {manifest.id}. expected={manifest.sha256} actual={actual}")
    return {'ok':True,'source_id':manifest.id,'authority_id':manifest.authority_id or manifest.id,
            'representation_id':manifest.representation_id,'name':manifest.name,
            'authority_type':manifest.authority_type,'edition':manifest.edition,'version':manifest.version,
            'upstream_revision':manifest.upstream_revision,
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
