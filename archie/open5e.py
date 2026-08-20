from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

import httpx
import yaml

from .config import settings
from .db import connect, initialize

RESOURCE_ENDPOINTS: dict[str, str] = {
    "classes": "classes",
    "subclasses": "classes",
    "species": "species",
    "spells": "spells",
    "backgrounds": "backgrounds",
    "feats": "feats",
    "equipment": "items",
    "magic_items": "magicitems",
    "rules": "rules",
    "conditions": "conditions",
    "creatures": "creatures",
}

# Alpha.3 deliberately supports only one import candidate. Expanding this set is
# an explicit release decision, not a runtime discovery side effect.
ALPHA5_ALLOWED_DOCUMENTS = {"srd-2024"}


class Open5eError(RuntimeError):
    pass


@dataclass(frozen=True)
class Open5eDocument:
    key: str
    name: str
    document_type: str | None
    publisher: dict[str, Any] | str | None
    license: dict[str, Any] | str | None
    game_system: dict[str, Any] | str | None
    author: str | None
    published_at: str | None
    permalink: str | None
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _first(obj: dict[str, Any], *keys: str, default=None):
    for key in keys:
        if key in obj and obj[key] is not None:
            return obj[key]
    return default


def _document_from_api(obj: dict[str, Any]) -> Open5eDocument:
    key = str(_first(obj, "key", "slug", default="")).strip()
    name = str(_first(obj, "name", "title", default=key)).strip()
    if not key:
        raise Open5eError(f"Open5e document is missing a key: {obj!r}")
    return Open5eDocument(
        key=key,
        name=name or key,
        document_type=_first(obj, "type", "document_type"),
        publisher=_first(obj, "publisher"),
        license=_first(obj, "license"),
        game_system=_first(obj, "game_system", "gamesystem", "ruleset"),
        author=_first(obj, "author"),
        published_at=_first(obj, "published_at", "published"),
        permalink=_first(obj, "permalink", "url"),
        raw=obj,
    )


class Open5eClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None, *, transport: httpx.BaseTransport | None = None):
        self.base_url = (base_url or settings.open5e_base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.open5e_timeout
        self.transport = transport

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                r = client.get(url, params=params)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            raise Open5eError(f"Open5e request failed at {url}: {exc}") from exc
        if not isinstance(data, dict):
            raise Open5eError(f"Open5e returned a non-object payload at {url}")
        return data

    def _paged(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        page = 1
        out: list[dict[str, Any]] = []
        base_params = dict(params or {})
        while True:
            request_params = {**base_params, "limit": 100, "page": page}
            data = self._get(path, request_params)
            results = data.get("results")
            if not isinstance(results, list):
                raise Open5eError(f"Open5e paginated payload at {path} has no results list")
            out.extend(x for x in results if isinstance(x, dict))
            count = data.get("count")
            if isinstance(count, int) and len(out) >= count:
                break
            if not results:
                break
            if data.get("next") in (None, "") and not (isinstance(count, int) and len(out) < count):
                break
            page += 1
            if page > 1000:
                raise Open5eError("Open5e pagination exceeded safety limit")
        return out

    def documents(self) -> list[Open5eDocument]:
        return [_document_from_api(x) for x in self._paged("documents/")]

    def document(self, document_key: str) -> Open5eDocument:
        for doc in self.documents():
            if doc.key == document_key:
                return doc
        raise Open5eError(f"Open5e document not found: {document_key}")

    def resource_count(self, endpoint: str, document_key: str, *, extra_params: dict[str, Any] | None = None) -> int | None:
        params: dict[str, Any] = {"document__key__in": document_key, "limit": 1, "fields": "key"}
        if extra_params:
            params.update(extra_params)
        data = self._get(f"{endpoint.strip('/')}/", params)
        count = data.get("count")
        if isinstance(count, int):
            return count
        results = data.get("results")
        return len(results) if isinstance(results, list) and not results else None

    def inventory_document(self, document_key: str) -> dict[str, int | None]:
        out: dict[str, int | None] = {}
        for label, endpoint in RESOURCE_ENDPOINTS.items():
            extra = {"is_subclass": "false"} if label == "classes" else {"is_subclass": "true"} if label == "subclasses" else None
            out[label] = self.resource_count(endpoint, document_key, extra_params=extra)
        return out

    def resources(self, label: str, document_key: str) -> list[dict[str, Any]]:
        if label not in RESOURCE_ENDPOINTS:
            raise Open5eError(f"Unsupported Open5e resource type: {label}")
        params: dict[str, Any] = {"document__key__in": document_key}
        if label == "classes": params["is_subclass"] = "false"
        elif label == "subclasses": params["is_subclass"] = "true"
        return self._paged(f"{RESOURCE_ENDPOINTS[label]}/", params)


def _canonical_json(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _stored_snapshot_content_hash(raw: dict[str, Any]) -> str:
    payload = dict(raw)
    payload.pop('imported_at', None)
    payload.pop('content_sha256', None)
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _snapshot_path(stamp: str) -> Path:
    return settings.open5e_discovery_dir / f"open5e-discovery-{stamp}.json"


def write_snapshot(snapshot: dict[str, Any]) -> Path:
    settings.open5e_discovery_dir.mkdir(parents=True, exist_ok=True)
    payload = dict(snapshot)
    payload.pop("snapshot_sha256", None)
    digest = hashlib.sha256(_canonical_json(payload)).hexdigest()
    payload["snapshot_sha256"] = digest
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = _snapshot_path(stamp)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    (settings.open5e_discovery_dir / "latest.json").write_text(text, encoding="utf-8")
    return path


def discover_open5e(client: Open5eClient | None = None) -> dict[str, Any]:
    client = client or Open5eClient()
    docs = client.documents()
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    documents = []
    for doc in docs:
        d = doc.to_dict(); d["resource_counts"] = client.inventory_document(doc.key); d.pop("raw", None); documents.append(d)
    snapshot: dict[str, Any] = {"schema_version":1,"provider":"open5e","api_version":"v2","base_url":client.base_url,
        "generated_at":generated,"imported_into_archie":False,"documents":documents,"resource_endpoints":RESOURCE_ENDPOINTS}
    path = write_snapshot(snapshot)
    saved = json.loads(path.read_text(encoding="utf-8")); saved["snapshot_path"] = str(path.relative_to(settings.root)); saved["document_count"] = len(documents)
    return saved


def load_latest_snapshot() -> dict[str, Any]:
    path = settings.open5e_discovery_dir / "latest.json"
    if not path.exists(): raise Open5eError("No Open5e discovery snapshot exists. Run: archie sources discover open5e")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("provider") != "open5e": raise Open5eError(f"Invalid Open5e discovery snapshot: {path}")
    return data


def inventory_from_snapshot(document_key: str | None = None) -> dict[str, Any]:
    data = load_latest_snapshot(); docs = data.get("documents", [])
    if document_key is not None:
        docs = [d for d in docs if d.get("key") == document_key]
        if not docs: raise Open5eError(f"Document not found in latest Open5e snapshot: {document_key}")
    return {"provider":"open5e","api_version":data.get("api_version"),"generated_at":data.get("generated_at"),
        "snapshot_sha256":data.get("snapshot_sha256"),"documents":docs,"document_count":len(docs),"imported_into_archie":False}


def _meta_name(value: Any) -> str | None:
    if isinstance(value, dict):
        v = value.get("name") or value.get("title") or value.get("key")
        return str(v) if v else None
    return str(value) if value else None


def _meta_url(value: Any) -> str | None:
    if isinstance(value, dict):
        v = value.get("url") or value.get("permalink")
        return str(v) if v else None
    return None


def _record_external_id(obj: dict[str, Any], label: str, index: int) -> str:
    value = _first(obj, "key", "slug", "id", "name")
    return str(value) if value is not None else f"{label}:{index}"


def _record_name(obj: dict[str, Any], fallback: str) -> str:
    return str(_first(obj, "name", "title", "key", default=fallback))


def _record_document_keys(obj: dict[str, Any]) -> tuple[str, ...] | None:
    """Resolve the Open5e document provenance shapes observed in SRD-2024.

    Real records use either ``document: {key: ...}`` or the scalar
    ``document: ...``. A sequence is never accepted, but resolving its members
    lets diagnostics distinguish an ambiguous value from other malformed data.
    """
    if "document" not in obj:
        return None
    value = obj["document"]
    if isinstance(value, str):
        key = value.strip()
        return (key,) if key else None
    if isinstance(value, dict):
        key = value.get("key")
        if not isinstance(key, str) or not key.strip():
            return None
        return (key.strip(),)
    if isinstance(value, (list, tuple)):
        keys: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                keys.append(item.strip())
            elif isinstance(item, dict) and isinstance(item.get("key"), str) and item["key"].strip():
                keys.append(item["key"].strip())
            else:
                return None
        return tuple(dict.fromkeys(keys)) if keys else None
    return None


def open5e_record_admission(obj: Any) -> str:
    """Classify one raw Open5e record before normalization."""
    if not isinstance(obj, dict):
        return "invalid_provenance"
    if isinstance(obj.get("document"), (list, tuple)):
        return "invalid_provenance"
    keys = _record_document_keys(obj)
    if not keys or len(keys) != 1:
        return "invalid_provenance"
    return "accepted" if keys[0] == "srd-2024" else "rejected_non_wotc"


def _normalize_open5e_resources(c, *, source_id: str, source_version_id: int,
                                edition: str | None, resources: Any, now: str) -> dict[str, int]:
    diagnostics = {
        "observed": 0,
        "accepted": 0,
        "rejected_non_wotc": 0,
        "invalid_provenance": 0,
        "normalization_failures": 0,
    }
    if not isinstance(resources, dict):
        diagnostics["normalization_failures"] += 1
        return diagnostics
    for label in sorted(resources):
        items = resources[label]
        if not isinstance(items, list):
            diagnostics["normalization_failures"] += 1
            continue
        for idx, obj in enumerate(items, 1):
            diagnostics["observed"] += 1
            admission = open5e_record_admission(obj)
            if admission != "accepted":
                diagnostics[admission] += 1
                continue
            try:
                ext = _record_external_id(obj, label, idx)
                name = _record_name(obj, ext)
                structured = json.dumps(obj, sort_keys=True, ensure_ascii=False)
                c.execute(
                    '''INSERT INTO content_records(source_id,source_version_id,external_id,content_type,name,edition,authority_id,representation_id,
                       upstream_id,upstream_path,normalization_schema_version,structured_json,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (source_id, source_version_id, ext, label, name, edition, 'wotc:srd-5.2.1', 'open5e:srd-2024',
                     ext, f'{label}/{ext}', 1, structured, now),
                )
            except (TypeError, ValueError, OverflowError, sqlite3.Error):
                diagnostics["normalization_failures"] += 1
                continue
            diagnostics["accepted"] += 1
    return diagnostics


def _ensure_alpha3_columns(c) -> None:
    initialize(c)
    cols={r[1] for r in c.execute("PRAGMA table_info(sources)")}
    for name, ddl in (
        ("approved", "ALTER TABLE sources ADD COLUMN approved INTEGER NOT NULL DEFAULT 1 CHECK(approved IN (0,1))"),
        ("license_status", "ALTER TABLE sources ADD COLUMN license_status TEXT NOT NULL DEFAULT 'present'"),
        ("provider", "ALTER TABLE sources ADD COLUMN provider TEXT"),
        ("provider_document_key", "ALTER TABLE sources ADD COLUMN provider_document_key TEXT"),
        ("authority_id", "ALTER TABLE sources ADD COLUMN authority_id TEXT"),
        ("representation_id", "ALTER TABLE sources ADD COLUMN representation_id TEXT"),
    ):
        if name not in cols: c.execute(ddl)
    version_cols={r[1] for r in c.execute("PRAGMA table_info(source_versions)")}
    if "upstream_revision" not in version_cols:
        c.execute("ALTER TABLE source_versions ADD COLUMN upstream_revision TEXT")
    record_cols={r[1] for r in c.execute("PRAGMA table_info(content_records)")}
    for name, ddl in (
        ("authority_id", "ALTER TABLE content_records ADD COLUMN authority_id TEXT"),
        ("representation_id", "ALTER TABLE content_records ADD COLUMN representation_id TEXT"),
        ("upstream_id", "ALTER TABLE content_records ADD COLUMN upstream_id TEXT"),
        ("upstream_path", "ALTER TABLE content_records ADD COLUMN upstream_path TEXT"),
        ("normalization_schema_version", "ALTER TABLE content_records ADD COLUMN normalization_schema_version INTEGER"),
    ):
        if name not in record_cols: c.execute(ddl)


def _write_import_snapshot(document: Open5eDocument, resources: dict[str, list[dict[str, Any]]], imported_at: str) -> tuple[Path, str, str]:
    source_id=f"open5e:{document.key}"
    payload={"schema_version":1,"provider":"open5e","api_version":"v2","source_id":source_id,"document_key":document.key,
             "document":document.raw,"resources":resources}
    content_sha=hashlib.sha256(_canonical_json(payload)).hexdigest()
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    source_dir=settings.open5e_import_dir / document.key
    raw_dir=source_dir / "raw"; raw_dir.mkdir(parents=True, exist_ok=True)
    filename=f"open5e-{document.key}-{stamp}.json"
    path=raw_dir / filename
    wrapper={**payload,"imported_at":imported_at,"content_sha256":content_sha}
    path.write_text(json.dumps(wrapper,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return path, content_sha, f"open5e-v2-{content_sha[:12]}"


def _write_import_manifest(document: Open5eDocument, raw_path: Path, content_sha: str, version: str) -> Path:
    source_dir=raw_path.parents[1]
    license_name=_meta_name(document.license); license_url=_meta_url(document.license)
    license_status="present" if license_name else "missing"
    manifest={
        "id":f"open5e:{document.key}","name":document.name,"source_type":"open5e_snapshot",
        "authority_type":"approved_supplement","authority_id":"wotc:srd-5.2.1","representation_id":"open5e:srd-2024",
        "edition":"2024" if "2024" in (_meta_name(document.game_system) or document.key) else None,
        "enabled":False,"approved":False,"license_status":license_status,"provider":"open5e","provider_document_key":document.key,
        "priority":80,"license_name":license_name,"license_url":license_url,"homepage_url":document.permalink,
        "version":{"version":version,"filename":str(raw_path.relative_to(source_dir)),"sha256":hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                   "upstream_revision":content_sha,
                   "source_uri":f"{settings.open5e_base_url}/documents/"}
    }
    path=source_dir / "source.yaml"
    path.write_text(yaml.safe_dump(manifest,sort_keys=False,allow_unicode=True),encoding="utf-8")
    return path


def import_open5e_document(document_key: str, client: Open5eClient | None = None) -> dict[str, Any]:
    if document_key not in ALPHA5_ALLOWED_DOCUMENTS:
        raise Open5eError(f"Alpha.5 import policy allows only: {', '.join(sorted(ALPHA5_ALLOWED_DOCUMENTS))}. Requested: {document_key}")
    if not settings.database.exists():
        raise Open5eError("Source Library database not found. Run: python -m archie.cli ingest")
    client=client or Open5eClient(); document=client.document(document_key)
    resources={label:client.resources(label,document_key) for label in RESOURCE_ENDPOINTS}
    imported_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    raw_path, content_sha, version=_write_import_snapshot(document,resources,imported_at)
    manifest_path=_write_import_manifest(document,raw_path,content_sha,version)
    source_id=f"open5e:{document_key}"
    license_name=_meta_name(document.license); license_url=_meta_url(document.license); license_status="present" if license_name else "missing"

    c=connect()
    try:
        with c:
            _ensure_alpha3_columns(c)
            now=imported_at
            existing=c.execute("SELECT id FROM sources WHERE id=?",(source_id,)).fetchone()
            if existing:
                c.execute('''UPDATE sources SET name=?,source_type='open5e_snapshot',authority_type='approved_supplement',
                             authority_id='wotc:srd-5.2.1',representation_id='open5e:srd-2024',edition=?,
                             enabled=0,approved=0,license_status=?,provider='open5e',provider_document_key=?,priority=80,
                             license_name=?,license_url=?,homepage_url=?,updated_at=? WHERE id=?''',
                          (document.name,"2024" if "2024" in (_meta_name(document.game_system) or document.key) else None,license_status,document_key,
                           license_name,license_url,document.permalink,now,source_id))
            else:
                c.execute('''INSERT INTO sources(id,name,source_type,authority_type,authority_id,representation_id,edition,enabled,approved,license_status,provider,provider_document_key,
                             priority,license_name,license_url,homepage_url,created_at,updated_at) VALUES(?,?,?,?,?,?,?,0,0,?,?,?,?,?,?,?,?,?)''',
                          (source_id,document.name,'open5e_snapshot','approved_supplement','wotc:srd-5.2.1','open5e:srd-2024',
                           "2024" if "2024" in (_meta_name(document.game_system) or document.key) else None,license_status,'open5e',document_key,80,
                           license_name,license_url,document.permalink,now,now))

            active=c.execute("SELECT id,content_sha256,version FROM source_versions WHERE source_id=? AND active=1",(source_id,)).fetchone()
            unchanged=bool(active and active['content_sha256']==content_sha)
            if unchanged:
                source_version_id=active['id']; version=active['version']
                c.execute("UPDATE source_versions SET upstream_revision=? WHERE id=?",(content_sha,source_version_id))
            else:
                c.execute("UPDATE source_versions SET active=0 WHERE source_id=? AND active=1",(source_id,))
                cur=c.execute('''INSERT INTO source_versions(source_id,version,imported_at,content_sha256,source_uri,filename,upstream_revision,active)
                                 VALUES(?,?,?,?,?,?,?,1)''',(source_id,version,now,content_sha,f"{client.base_url}/documents/",str(raw_path.relative_to(settings.root)),content_sha))
                source_version_id=cur.lastrowid
            # Import always disables the source. Remove any previously materialized
            # evidence, then rebuild the active normalized records through the same
            # per-record admission gate even when the raw content is unchanged.
            c.execute("DELETE FROM evidence_chunks WHERE source_id=?",(source_id,))
            c.execute("DELETE FROM content_records WHERE source_id=? AND source_version_id=?",(source_id,source_version_id))
            diagnostics=_normalize_open5e_resources(c,source_id=source_id,source_version_id=source_version_id,
                                                    edition='2024',resources=resources,now=now)
            record_count=c.execute("SELECT count(*) FROM content_records WHERE source_id=? AND source_version_id=?",(source_id,source_version_id)).fetchone()[0]
            evidence_count=c.execute("SELECT count(*) FROM evidence_chunks WHERE source_id=?",(source_id,)).fetchone()[0]
    finally:
        c.close()
    return {"ok":True,"source_id":source_id,"document_key":document_key,"version":version,"content_sha256":content_sha,
            "raw_snapshot":str(raw_path.relative_to(settings.root)),"manifest":str(manifest_path.relative_to(settings.root)),
            "content_records":record_count,"evidence_chunks":evidence_count,"approved":False,"enabled":False,
            "license_status":license_status,"automatic_approval_blocked":True,"unchanged":unchanged,
            "diagnostics":diagnostics}


def rehydrate_open5e_imports(c, imported_at: str | None = None) -> dict[str, Any]:
    """Restore disabled Open5e structured imports after a generated index rebuild.

    Persistent storage is the source manifest plus raw JSON snapshot. SQLite is
    generated and can be rebuilt without losing imported content. Enabled, approved imports have evidence chunks reconstructed in alpha.5.
    """
    from .source import discover_source_manifests, verify_manifest

    now = imported_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    restored_sources = 0
    restored_records = 0
    diagnostics = {
        "observed": 0,
        "accepted": 0,
        "rejected_non_wotc": 0,
        "invalid_provenance": 0,
        "normalization_failures": 0,
    }
    _ensure_alpha3_columns(c)

    for manifest in discover_source_manifests():
        if manifest.source_type != 'open5e_snapshot':
            continue
        verify_manifest(manifest)
        raw = json.loads(manifest.content_path.read_text(encoding='utf-8'))
        if raw.get('provider') != 'open5e' or raw.get('document_key') != manifest.provider_document_key:
            raise Open5eError(f"Invalid stored Open5e snapshot for {manifest.id}")
        content_sha = str(raw.get('content_sha256') or '')
        if not content_sha:
            raise Open5eError(f"Stored Open5e snapshot lacks content_sha256: {manifest.id}")
        if content_sha != _stored_snapshot_content_hash(raw):
            raise Open5eError(f"Stored Open5e snapshot content SHA-256 mismatch: {manifest.id}")
        if manifest.upstream_revision != content_sha:
            raise Open5eError(f"Stored Open5e snapshot revision does not match canonical content: {manifest.id}")

        existing = c.execute("SELECT id FROM sources WHERE id=?", (manifest.id,)).fetchone()
        source_values = (
            manifest.name, manifest.source_type, manifest.authority_type, manifest.authority_id,
            manifest.representation_id, manifest.edition, 1 if manifest.enabled else 0,
            1 if manifest.approved else 0, manifest.license_status, manifest.provider,
            manifest.provider_document_key, manifest.priority, manifest.license_name,
            manifest.license_url, manifest.homepage_url,
        )
        if existing:
            c.execute(
                '''UPDATE sources SET name=?,source_type=?,authority_type=?,authority_id=?,representation_id=?,edition=?,
                   enabled=?,approved=?,license_status=?,provider=?,provider_document_key=?,priority=?,license_name=?,license_url=?,
                   homepage_url=?,updated_at=? WHERE id=?''',
                (*source_values, now, manifest.id),
            )
        else:
            c.execute(
                '''INSERT INTO sources(id,name,source_type,authority_type,authority_id,representation_id,edition,enabled,approved,license_status,provider,provider_document_key,
                   priority,license_name,license_url,homepage_url,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (manifest.id, *source_values, now, now),
            )
        active = c.execute(
            "SELECT id,content_sha256 FROM source_versions WHERE source_id=? AND active=1",
            (manifest.id,),
        ).fetchone()
        if active and active['content_sha256'] == content_sha:
            version_id = active['id']
            c.execute(
                '''UPDATE source_versions SET version=?,source_uri=?,filename=?,upstream_revision=? WHERE id=?''',
                (manifest.version, manifest.source_uri, manifest.filename, manifest.upstream_revision, version_id),
            )
        else:
            c.execute("UPDATE source_versions SET active=0 WHERE source_id=? AND active=1", (manifest.id,))
            cur = c.execute(
                '''INSERT INTO source_versions(source_id,version,imported_at,content_sha256,source_uri,filename,upstream_revision,active)
                   VALUES(?,?,?,?,?,?,?,1)''',
                (manifest.id, manifest.version, now, content_sha, manifest.source_uri,
                 manifest.filename, manifest.upstream_revision),
            )
            version_id = cur.lastrowid
        c.execute("DELETE FROM evidence_chunks WHERE source_id=?", (manifest.id,))
        c.execute(
            "DELETE FROM content_records WHERE source_id=? AND source_version_id=?",
            (manifest.id, version_id),
        )
        resources = raw.get('resources') or {}
        source_diagnostics = _normalize_open5e_resources(
            c, source_id=manifest.id, source_version_id=version_id,
            edition=manifest.edition, resources=resources, now=now,
        )
        for key in diagnostics:
            diagnostics[key] += source_diagnostics[key]
        restored_records += source_diagnostics['accepted']
        if manifest.enabled:
            if not manifest.approved or manifest.license_status != 'present':
                raise Open5eError(f'Enabled stored source is not approved/licensed: {manifest.id}')
            from .structured_evidence import materialize_structured_evidence
            materialize_structured_evidence(c, manifest.id)
        restored_sources += 1

    return {'sources': restored_sources, 'content_records': restored_records, 'diagnostics': diagnostics}
