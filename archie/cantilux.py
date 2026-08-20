from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import sqlite3
import subprocess
import tempfile
from typing import Any

from .db import connect, initialize


SOURCE_ID = "cantilux:dnd-srd-json"
AUTHORITY_ID = "wotc:srd-5.2.1"
REPRESENTATION_ID = SOURCE_ID
PROVIDER = "cantilux"
REPOSITORY = "https://github.com/Cantilux/dnd-srd-json"
UPSTREAM_REVISION = "df536fe94c92cff49cc531f7283f6995b881fefa"
UPSTREAM_PATH = "data/srd.json"
SRD_VERSION = "5.2.1"
RULES_REVISION = "2024"
LICENSE = "CC-BY-4.0"
OFFICIAL_SRD_URL = "https://www.dndbeyond.com/srd"
NORMALIZATION_SCHEMA_VERSION = 1
AREA_EFFECT_COLLECTION = "areas-of-effect"
AREA_EFFECT_INTERNAL_DEFECT = "area-of-effects"
AREA_EFFECT_RESOURCE_IDS = frozenset({"cone", "cube", "cylinder", "emanation", "line", "sphere"})
# Audited identities from resource-index.json and search-index.json at the
# pinned revision. The canonical bundle does not embed either generated index.
PINNED_RESOURCE_INDEX_MEMBERS = frozenset((AREA_EFFECT_COLLECTION, item) for item in AREA_EFFECT_RESOURCE_IDS)
PINNED_SEARCH_INDEX_IDS = frozenset(f"{AREA_EFFECT_COLLECTION}:{item}" for item in AREA_EFFECT_RESOURCE_IDS)
DIAGNOSTIC_KEYS = (
    "observed", "accepted", "rejected_non_wotc", "invalid_provenance",
    "normalization_failures",
)


class CantiluxError(RuntimeError):
    pass


def _run_git(*args: str, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise CantiluxError(f"Cantilux acquisition Git command failed: {detail.strip()}") from exc
    return result.stdout.strip()


def _load_snapshot(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw_bytes = Path(path).read_bytes()
        snapshot = json.loads(raw_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        raise CantiluxError(f"Cannot read Cantilux snapshot: {exc}") from exc
    if not isinstance(snapshot, dict):
        raise CantiluxError("Cantilux snapshot must be a JSON object")
    return snapshot, raw_bytes


def _validate_corpus(snapshot: Any) -> dict[str, Any]:
    """Validate the corpus-level provenance inherited by every resource.

    Cantilux records do not repeat authority or license metadata. The pinned
    bundle's manifest and metadata identify the complete corpus, while each
    record's ``source`` object supplies its stable document/section lineage.
    """
    if not isinstance(snapshot, dict):
        raise CantiluxError("Cantilux snapshot must be a JSON object")
    manifest = snapshot.get("manifest")
    metadata = snapshot.get("metadata")
    if not isinstance(manifest, dict) or not isinstance(metadata, dict):
        raise CantiluxError("Cantilux snapshot lacks required corpus provenance")
    required = {
        "name": "dnd-srd-json",
        "srdVersion": SRD_VERSION,
        "rulesRevision": RULES_REVISION,
        "officialSrdUrl": OFFICIAL_SRD_URL,
        "license": LICENSE,
    }
    for key, expected in required.items():
        if manifest.get(key) != expected or metadata.get(key) != expected:
            raise CantiluxError(f"Cantilux corpus provenance mismatch: {key}")
    if not isinstance(snapshot.get("documents"), list) or not isinstance(snapshot.get("sections"), list):
        raise CantiluxError("Cantilux corpus has malformed documents or sections")
    if not isinstance(snapshot.get("collections"), dict):
        raise CantiluxError("Cantilux corpus has malformed collections")
    return snapshot


def cantilux_record_admission(
    record: Any,
    collection_id: Any,
    *,
    collection: Any = None,
    manifest_collection: Any = None,
    documents: Any = None,
    sections: Any = None,
) -> str:
    """Validate stable resource identity and lineage under corpus provenance."""
    if not isinstance(record, dict) or not isinstance(collection_id, str) or not collection_id:
        return "invalid_provenance"
    upstream_id = record.get("id")
    internal_collection = record.get("collection")
    source = record.get("source")
    if not isinstance(upstream_id, str) or not upstream_id.strip():
        return "invalid_provenance"
    if not isinstance(source, dict):
        return "invalid_provenance"
    document_id = source.get("documentId")
    section_id = source.get("sectionId")
    path = source.get("path")
    if not isinstance(document_id, str) or not document_id.strip():
        return "invalid_provenance"
    if not isinstance(section_id, str) or not section_id.strip():
        return "invalid_provenance"
    # Table resources omit the human-readable path but retain document and
    # section IDs. Other resources provide it; when present it must be valid.
    if path is not None and (not isinstance(path, list) or not path
                             or not all(isinstance(x, str) and x.strip() for x in path)):
        return "invalid_provenance"
    if documents is not None and document_id not in documents:
        return "invalid_provenance"
    if sections is not None:
        section = sections.get(section_id) if isinstance(sections, dict) else None
        if not isinstance(section, dict) or section.get("documentId") != document_id:
            return "invalid_provenance"
    if internal_collection == collection_id:
        return "accepted"
    if not _area_effect_defect_is_corroborated(
        record, collection_id, collection, manifest_collection, documents, sections,
    ):
        return "invalid_provenance"
    return "accepted"


def _area_effect_defect_is_corroborated(
    record: dict[str, Any], collection_id: str, collection: Any,
    manifest_collection: Any, documents: Any, sections: Any,
) -> bool:
    """Recognize exactly one audited defect in the pinned Cantilux corpus."""
    upstream_id = record["id"]
    if (collection_id != AREA_EFFECT_COLLECTION
            or record.get("collection") != AREA_EFFECT_INTERNAL_DEFECT
            or upstream_id not in AREA_EFFECT_RESOURCE_IDS
            or not isinstance(collection, dict)
            or collection.get("id") != AREA_EFFECT_COLLECTION
            or not isinstance(manifest_collection, dict)
            or documents is None or sections is None
            or (AREA_EFFECT_COLLECTION, upstream_id) not in PINNED_RESOURCE_INDEX_MEMBERS
            or f"{AREA_EFFECT_COLLECTION}:{upstream_id}" not in PINNED_SEARCH_INDEX_IDS):
        return False
    item_ids = collection.get("itemIds")
    manifest_ids = manifest_collection.get("itemIds")
    items = collection.get("items")
    if (not isinstance(item_ids, list) or item_ids.count(upstream_id) != 1
            or not isinstance(manifest_ids, list) or manifest_ids.count(upstream_id) != 1
            or not isinstance(items, list)):
        return False
    lightweight = [item for item in items if isinstance(item, dict) and item.get("id") == upstream_id]
    return (len(lightweight) == 1
            and lightweight[0].get("collection") == AREA_EFFECT_COLLECTION
            and lightweight[0].get("name") == record.get("name"))


def _resource_path(collection_id: str, upstream_id: str) -> str:
    # These paths are part of Cantilux's documented granular-resource API.
    return PurePosixPath("data", "resources", collection_id, f"{upstream_id}.json").as_posix()


def _normalize(c, *, snapshot: dict[str, Any], source_version_id: int, now: str) -> tuple[dict[str, int], dict[str, int]]:
    diagnostics = {key: 0 for key in DIAGNOSTIC_KEYS}
    by_collection: dict[str, int] = {}
    collections = snapshot["collections"]
    manifest_collections = snapshot["manifest"].get("collections", {})
    documents = {item.get("id") for item in snapshot["documents"] if isinstance(item, dict)}
    sections = {item.get("id"): item for item in snapshot["sections"]
                if isinstance(item, dict) and isinstance(item.get("id"), str)}
    for collection_id in sorted(collections):
        collection = collections[collection_id]
        if not isinstance(collection_id, str) or not isinstance(collection, dict):
            diagnostics["normalization_failures"] += 1
            continue
        items = collection.get("items")
        resources = collection.get("resources")
        item_ids = collection.get("itemIds")
        declared_count = collection.get("count")
        if (not isinstance(items, list) or not isinstance(resources, list) or not isinstance(item_ids, list)
                or declared_count != len(items) or declared_count != len(resources)
                or item_ids != [x.get("id") if isinstance(x, dict) else None for x in items]
                or item_ids != [x.get("id") if isinstance(x, dict) else None for x in resources]):
            diagnostics["normalization_failures"] += 1
            continue
        for record in resources:
            diagnostics["observed"] += 1
            admission = cantilux_record_admission(
                record, collection_id, collection=collection,
                manifest_collection=manifest_collections.get(collection_id),
                documents=documents, sections=sections,
            )
            if admission != "accepted":
                diagnostics[admission] += 1
                continue
            try:
                upstream_id = record["id"].strip()
                name = record.get("name")
                c.execute(
                    '''INSERT INTO content_records(source_id,source_version_id,external_id,content_type,name,edition,authority_id,representation_id,
                       upstream_id,upstream_path,normalization_schema_version,structured_json,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (SOURCE_ID, source_version_id, upstream_id, collection_id,
                     str(name) if name is not None else upstream_id, RULES_REVISION,
                     AUTHORITY_ID, REPRESENTATION_ID, upstream_id,
                     _resource_path(collection_id, upstream_id), NORMALIZATION_SCHEMA_VERSION,
                     json.dumps(record, sort_keys=True, ensure_ascii=False), now),
                )
            except (KeyError, TypeError, ValueError, OverflowError, sqlite3.Error):
                diagnostics["normalization_failures"] += 1
                continue
            diagnostics["accepted"] += 1
            by_collection[collection_id] = by_collection.get(collection_id, 0) + 1
    return diagnostics, by_collection


def build_cantilux_snapshot(checkout: Path) -> dict[str, Any]:
    """Verify a pinned checkout and describe its canonical upstream bundle."""
    checkout = Path(checkout).resolve()
    revision = _run_git("rev-parse", "HEAD", cwd=checkout)
    if revision != UPSTREAM_REVISION:
        raise CantiluxError(f"Cantilux checkout is not pinned to {UPSTREAM_REVISION}: {revision}")
    snapshot, raw_bytes = _load_snapshot(checkout / UPSTREAM_PATH)
    _validate_corpus(snapshot)
    return {
        "snapshot_bytes": raw_bytes,
        "snapshot_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "upstream_revision": revision,
        "documents": len(snapshot["documents"]),
        "sections": len(snapshot["sections"]),
        "collections": len(snapshot["collections"]),
        "resources": sum(len(x.get("resources", [])) for x in snapshot["collections"].values() if isinstance(x, dict)),
    }


def write_cantilux_snapshot(checkout: Path, output: Path) -> dict[str, Any]:
    result = build_cantilux_snapshot(checkout)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(result.pop("snapshot_bytes"))
    return {"snapshot_path": str(output), **result}


def acquire_cantilux_snapshot(output: Path, checkout: Path | None = None) -> dict[str, Any]:
    """Acquire only the canonical bundle from the immutable upstream commit."""
    if checkout is not None:
        return write_cantilux_snapshot(checkout, output)
    with tempfile.TemporaryDirectory(prefix="archie-cantilux-") as temporary:
        clone = Path(temporary) / "dnd-srd-json"
        clone.mkdir()
        _run_git("init", cwd=clone)
        _run_git("remote", "add", "origin", REPOSITORY, cwd=clone)
        _run_git("fetch", "--depth", "1", "--filter=blob:none", "origin", UPSTREAM_REVISION, cwd=clone)
        _run_git("sparse-checkout", "set", "--no-cone", f"/{UPSTREAM_PATH}", cwd=clone)
        _run_git("checkout", "--detach", "FETCH_HEAD", cwd=clone)
        return write_cantilux_snapshot(clone, output)


def import_cantilux_snapshot(
    path: Path, *, connection=None, imported_at: str | None = None,
    upstream_revision: str = UPSTREAM_REVISION,
) -> dict[str, Any]:
    snapshot, raw_bytes = _load_snapshot(path)
    _validate_corpus(snapshot)
    if (not isinstance(upstream_revision, str) or len(upstream_revision) != 40
            or any(c not in "0123456789abcdef" for c in upstream_revision)):
        raise CantiluxError("Cantilux import requires an immutable lowercase Git commit")
    if upstream_revision != UPSTREAM_REVISION:
        raise CantiluxError("Cantilux import revision is not the pinned upstream commit")
    content_sha = hashlib.sha256(raw_bytes).hexdigest()
    now = imported_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    own_connection = connection is None
    c = connection or connect()
    try:
        initialize(c)
        with c:
            existing = c.execute("SELECT id FROM sources WHERE id=?", (SOURCE_ID,)).fetchone()
            values = ("Cantilux representation of SRD 5.2.1", "cantilux_snapshot", "approved_supplement",
                      AUTHORITY_ID, REPRESENTATION_ID, RULES_REVISION, 0, 1, "present", PROVIDER,
                      "dnd-srd-json", 85, LICENSE, "https://creativecommons.org/licenses/by/4.0/", REPOSITORY)
            if existing:
                c.execute('''UPDATE sources SET name=?,source_type=?,authority_type=?,authority_id=?,representation_id=?,edition=?,
                             enabled=?,approved=?,license_status=?,provider=?,provider_document_key=?,priority=?,license_name=?,license_url=?,
                             homepage_url=?,updated_at=? WHERE id=?''', (*values, now, SOURCE_ID))
            else:
                c.execute('''INSERT INTO sources(id,name,source_type,authority_type,authority_id,representation_id,edition,enabled,approved,
                             license_status,provider,provider_document_key,priority,license_name,license_url,homepage_url,created_at,updated_at)
                             VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (SOURCE_ID, *values, now, now))
            active = c.execute("SELECT id,content_sha256 FROM source_versions WHERE source_id=? AND active=1", (SOURCE_ID,)).fetchone()
            unchanged = bool(active and active["content_sha256"] == content_sha)
            if unchanged:
                version_id = active["id"]
            else:
                c.execute("UPDATE source_versions SET active=0 WHERE source_id=? AND active=1", (SOURCE_ID,))
                cur = c.execute('''INSERT INTO source_versions(source_id,version,imported_at,content_sha256,source_uri,filename,upstream_revision,active)
                                   VALUES(?,?,?,?,?,?,?,1)''',
                                (SOURCE_ID, f"cantilux-{upstream_revision[:12]}", now, content_sha,
                                 f"{REPOSITORY}/blob/{upstream_revision}/{UPSTREAM_PATH}", str(path), upstream_revision))
                version_id = cur.lastrowid
            c.execute("DELETE FROM evidence_chunks WHERE source_id=?", (SOURCE_ID,))
            c.execute("DELETE FROM content_records WHERE source_id=? AND source_version_id=?", (SOURCE_ID, version_id))
            diagnostics, by_collection = _normalize(c, snapshot=snapshot, source_version_id=version_id, now=now)
            count = c.execute("SELECT count(*) FROM content_records WHERE source_id=? AND source_version_id=?",
                              (SOURCE_ID, version_id)).fetchone()[0]
    finally:
        if own_connection:
            c.close()
    return {"ok": True, "source_id": SOURCE_ID, "content_sha256": content_sha,
            "upstream_revision": upstream_revision, "content_records": count,
            "evidence_chunks": 0, "unchanged": unchanged, "diagnostics": diagnostics,
            "documents": len(snapshot["documents"]), "sections": len(snapshot["sections"]),
            "collections": len(snapshot["collections"]), "records_by_collection": by_collection}


def rehydrate_cantilux_imports(c, imported_at: str | None = None) -> dict[str, Any]:
    from .source import discover_source_manifests, verify_manifest

    totals = {key: 0 for key in DIAGNOSTIC_KEYS}
    sources = records = 0
    by_collection: dict[str, int] = {}
    for manifest in discover_source_manifests():
        if manifest.source_type != "cantilux_snapshot":
            continue
        verify_manifest(manifest)
        if manifest.upstream_revision != UPSTREAM_REVISION:
            raise CantiluxError("Stored Cantilux snapshot revision is not the pinned upstream commit")
        result = import_cantilux_snapshot(
            manifest.content_path, connection=c, imported_at=imported_at,
            upstream_revision=manifest.upstream_revision,
        )
        sources += 1
        records += result["content_records"]
        for key in totals:
            totals[key] += result["diagnostics"][key]
        for key, value in result["records_by_collection"].items():
            by_collection[key] = by_collection.get(key, 0) + value
    return {"sources": sources, "content_records": records, "diagnostics": totals,
            "records_by_collection": by_collection}
