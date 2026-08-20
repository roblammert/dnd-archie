from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import sqlite3
import subprocess
import tempfile
from typing import Any

import yaml

from .db import connect, initialize


SOURCE_ID = "foundry:srd-5.2"
AUTHORITY_ID = "wotc:srd-5.2.1"
REPRESENTATION_ID = "foundry:srd-5.2"
PROVIDER = "foundry-dnd5e"
REPOSITORY = "https://github.com/foundryvtt/dnd5e"
UPSTREAM_REVISION = "905c29bcab6a0c6622f3ac6b70f9e040bacbedac"
UPSTREAM_RELEASE = "release-5.2.0"
SRD_SOURCE_BOOK = "SRD 5.2"
ALLOWED_PACKS = frozenset({
    "actors24", "classes24", "equipment24", "feats24", "monsterfeatures24",
    "origins24", "spells24",
})
DIAGNOSTIC_KEYS = (
    "observed", "accepted", "rejected_non_wotc", "invalid_provenance",
    "normalization_failures",
)
EXCLUDED_PACKS = ("content24", "tables24")


class FoundryError(RuntimeError):
    pass


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _content_hash(snapshot: dict[str, Any]) -> str:
    payload = dict(snapshot)
    payload.pop("content_sha256", None)
    payload.pop("imported_at", None)
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _run_git(*args: str, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise FoundryError(f"Foundry acquisition Git command failed: {detail.strip()}") from exc
    return result.stdout.strip()


def build_foundry_snapshot(checkout: Path) -> dict[str, Any]:
    """Build the canonical raw snapshot from a checkout at the pinned commit."""
    checkout = Path(checkout).resolve()
    revision = _run_git("rev-parse", "HEAD", cwd=checkout)
    if revision != UPSTREAM_REVISION:
        raise FoundryError(f"Foundry checkout is not pinned to {UPSTREAM_REVISION}: {revision}")
    try:
        system_manifest = json.loads((checkout / "system.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FoundryError(f"Cannot read pinned Foundry system.json: {exc}") from exc
    if system_manifest.get("id") != "dnd5e" or system_manifest.get("version") != "5.2.0":
        raise FoundryError("Pinned Foundry system manifest identity/version mismatch")
    upstream_packs = {
        pack.get("name"): pack for pack in system_manifest.get("packs", [])
        if isinstance(pack, dict) and isinstance(pack.get("name"), str)
    }
    selected_packs = []
    records = []
    folder_metadata = []
    by_pack: dict[str, dict[str, int]] = {}
    for pack_name in sorted(ALLOWED_PACKS):
        pack = upstream_packs.get(pack_name)
        if not isinstance(pack, dict):
            raise FoundryError(f"Pinned Foundry system manifest lacks permitted pack: {pack_name}")
        selected_packs.append(pack)
        source_dir = checkout / "packs" / "_source" / pack_name
        paths = sorted(source_dir.rglob("*.yml"), key=lambda p: p.relative_to(checkout).as_posix())
        if not paths:
            raise FoundryError(f"Pinned Foundry pack has no YAML source files: {pack_name}")
        pack_counts = {"upstream_files_observed": len(paths), "snapshot_records": 0, "folder_metadata_files": 0}
        for path in paths:
            upstream_path = path.relative_to(checkout).as_posix()
            raw_bytes = path.read_bytes()
            try:
                document = yaml.safe_load(raw_bytes)
            except yaml.YAMLError as exc:
                raise FoundryError(f"Malformed upstream Foundry YAML at {upstream_path}: {exc}") from exc
            if not isinstance(document, dict):
                raise FoundryError(f"Non-object upstream Foundry YAML at {upstream_path}")
            item = {"pack": pack_name, "path": upstream_path,
                    "upstream_file_sha256": hashlib.sha256(raw_bytes).hexdigest(), "document": document}
            if path.name == "_folder.yml" or str(document.get("_key", "")).startswith("!folders!"):
                folder_metadata.append(item)
                pack_counts["folder_metadata_files"] += 1
            else:
                records.append(item)
                pack_counts["snapshot_records"] += 1
        by_pack[pack_name] = pack_counts
    snapshot = {
        "schema_version": 1,
        "provider": PROVIDER,
        "repository": REPOSITORY,
        "upstream_release": UPSTREAM_RELEASE,
        "upstream_revision": UPSTREAM_REVISION,
        "system_manifest": {"id": system_manifest["id"], "version": system_manifest["version"], "packs": selected_packs},
        "acquisition": {
            "packs": by_pack,
            "permitted_packs": sorted(ALLOWED_PACKS),
            "excluded_packs": list(EXCLUDED_PACKS),
            "upstream_files_observed": sum(x["upstream_files_observed"] for x in by_pack.values()),
            "snapshot_records": len(records),
            "folder_metadata_files": len(folder_metadata),
        },
        "folder_metadata": folder_metadata,
        "records": records,
    }
    admission = {key: 0 for key in DIAGNOSTIC_KEYS}
    snapshot_packs = _pack_map(snapshot)
    for entry in records:
        admission["observed"] += 1
        outcome = _snapshot_v1_diagnostic_admission(entry, snapshot_packs.get(entry["pack"]))
        admission[outcome] += 1
        by_pack[entry["pack"]].setdefault(outcome, 0)
        by_pack[entry["pack"]][outcome] += 1
    for counts in by_pack.values():
        for key in ("accepted", "rejected_non_wotc", "invalid_provenance", "normalization_failures"):
            counts.setdefault(key, 0)
    snapshot["acquisition"].update({key: admission[key] for key in DIAGNOSTIC_KEYS})
    snapshot["content_sha256"] = _content_hash(snapshot)
    return snapshot


def write_foundry_snapshot(checkout: Path, output: Path) -> dict[str, Any]:
    snapshot = build_foundry_snapshot(checkout)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"snapshot_path": str(output), "snapshot_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "content_sha256": snapshot["content_sha256"], **snapshot["acquisition"]}


def acquire_foundry_snapshot(output: Path, checkout: Path | None = None) -> dict[str, Any]:
    """Acquire the pinned sparse source tree, or build from a verified checkout."""
    if checkout is not None:
        return write_foundry_snapshot(checkout, output)
    with tempfile.TemporaryDirectory(prefix="archie-foundry-") as temporary:
        clone = Path(temporary) / "dnd5e"
        _run_git("clone", "--depth", "1", "--branch", UPSTREAM_RELEASE, "--filter=blob:none", "--sparse", REPOSITORY, str(clone))
        sparse_paths = ["/system.json", *(f"/packs/_source/{pack}/" for pack in sorted(ALLOWED_PACKS))]
        _run_git("sparse-checkout", "set", "--no-cone", *sparse_paths, cwd=clone)
        return write_foundry_snapshot(clone, output)


def _pack_map(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    manifest = snapshot.get("system_manifest")
    packs = manifest.get("packs") if isinstance(manifest, dict) else None
    if not isinstance(packs, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for pack in packs:
        if isinstance(pack, dict) and isinstance(pack.get("name"), str):
            name = pack["name"].strip()
            if name and name not in result:
                result[name] = pack
            elif name:
                # A duplicate makes the pack identity ambiguous.
                result[name] = {}
    return result


def foundry_record_admission(entry: Any, pack_metadata: Any) -> str:
    """Classify a Foundry source record using observed pack inheritance.

    Foundry D&D5e release 5.2.0 leaves ``system.source.book`` empty on SRD
    records and inherits ``SRD 5.2`` from the compendium definition in
    ``system.json``. Both layers are required here; pack names alone are never
    authority evidence.
    """
    if not isinstance(entry, dict) or not isinstance(pack_metadata, dict):
        return "invalid_provenance"
    pack = entry.get("pack")
    path = entry.get("path")
    document = entry.get("document")
    if not isinstance(pack, str) or not pack.strip() or not isinstance(path, str) or not path.strip():
        return "invalid_provenance"
    if pack not in ALLOWED_PACKS:
        return "rejected_non_wotc"
    expected_prefix = PurePosixPath("packs", "_source", pack)
    candidate = PurePosixPath(path)
    if candidate.is_absolute() or ".." in candidate.parts or candidate.suffix != ".yml" or expected_prefix not in candidate.parents:
        return "invalid_provenance"
    if not isinstance(document, dict) or not isinstance(document.get("_id"), str) or not document["_id"].strip():
        return "invalid_provenance"

    flags = pack_metadata.get("flags")
    dnd5e = flags.get("dnd5e") if isinstance(flags, dict) else None
    inherited_book = dnd5e.get("sourceBook") if isinstance(dnd5e, dict) else None
    if not isinstance(inherited_book, str) or not inherited_book.strip():
        return "invalid_provenance"
    if inherited_book != SRD_SOURCE_BOOK:
        return "rejected_non_wotc"
    if pack_metadata.get("name") != pack or pack_metadata.get("path") != f"packs/{pack}":
        return "invalid_provenance"

    system = document.get("system")
    source = system.get("source") if isinstance(system, dict) else None
    if not isinstance(source, dict):
        return "invalid_provenance"
    # The rules version is explicit record metadata and is never inherited.
    # A 2014 record may still be WotC content, but it is incompatible with this
    # 2024 representation, so it is classified as invalid provenance.
    if source.get("rules") != "2024":
        return "invalid_provenance"
    book = source.get("book", "")
    if book is None:
        book = ""
    if not isinstance(book, str):
        return "invalid_provenance"
    effective_book = book if book else inherited_book
    if effective_book != SRD_SOURCE_BOOK:
        return "rejected_non_wotc"
    # The pinned repository establishes CC-BY-4.0 at the SRD 5.2 work level;
    # records need not repeat it. An explicit conflicting license still fails.
    license_name = source.get("license", "")
    if license_name is None:
        license_name = ""
    if not isinstance(license_name, str) or (license_name and license_name != "CC-BY-4.0"):
        return "invalid_provenance"
    return "accepted"


def _snapshot_v1_diagnostic_admission(entry: Any, pack_metadata: Any) -> str:
    """Preserve snapshot-schema-v1 acquisition diagnostics byte-for-byte.

    Those diagnostics recorded raw field completeness at acquisition time.
    Import admission now resolves Foundry's documented source-book inheritance,
    but changing this historical snapshot annotation would change raw bytes.
    """
    document = entry.get("document") if isinstance(entry, dict) else None
    system = document.get("system") if isinstance(document, dict) else None
    source = system.get("source") if isinstance(system, dict) else None
    outcome = foundry_record_admission(entry, pack_metadata)
    if outcome == "invalid_provenance":
        return outcome
    # Snapshot v1 checked license completeness before inspecting an explicit
    # book override, so its one MM 2024 record was historically "invalid".
    if not isinstance(source, dict) or source.get("license") != "CC-BY-4.0":
        return "invalid_provenance"
    book = source.get("book")
    if not isinstance(book, str) or book not in ("", SRD_SOURCE_BOOK):
        return "rejected_non_wotc"
    return "accepted"


def _normalize(c, *, snapshot: dict[str, Any], source_version_id: int, now: str) -> dict[str, int]:
    diagnostics = {key: 0 for key in DIAGNOSTIC_KEYS}
    records = snapshot.get("records")
    if not isinstance(records, list):
        diagnostics["normalization_failures"] += 1
        return diagnostics
    packs = _pack_map(snapshot)
    for entry in records:
        diagnostics["observed"] += 1
        pack_name = entry.get("pack") if isinstance(entry, dict) else None
        admission = foundry_record_admission(entry, packs.get(pack_name))
        if admission != "accepted":
            diagnostics[admission] += 1
            continue
        try:
            document = entry["document"]
            upstream_id = document["_id"].strip()
            name = document.get("name")
            content_type = document.get("type") or packs[pack_name].get("type") or pack_name
            c.execute(
                '''INSERT INTO content_records(source_id,source_version_id,external_id,content_type,name,edition,authority_id,representation_id,
                   upstream_id,upstream_path,normalization_schema_version,structured_json,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (SOURCE_ID, source_version_id, upstream_id, str(content_type), str(name) if name is not None else upstream_id,
                 "2024", AUTHORITY_ID, REPRESENTATION_ID, upstream_id, entry["path"], 1,
                 json.dumps(document, sort_keys=True, ensure_ascii=False), now),
            )
        except (KeyError, TypeError, ValueError, OverflowError, sqlite3.Error):
            diagnostics["normalization_failures"] += 1
            continue
        diagnostics["accepted"] += 1
    return diagnostics


def _validate_snapshot(snapshot: Any, *, revision: str | None = None) -> dict[str, Any]:
    if not isinstance(snapshot, dict) or snapshot.get("provider") != PROVIDER:
        raise FoundryError("Invalid Foundry D&D5e snapshot provider")
    if snapshot.get("repository") != REPOSITORY:
        raise FoundryError("Unknown Foundry D&D5e repository identity")
    upstream = snapshot.get("upstream_revision")
    if not isinstance(upstream, str) or len(upstream) != 40 or any(c not in "0123456789abcdef" for c in upstream):
        raise FoundryError("Foundry snapshot requires an immutable lowercase Git commit")
    if revision is not None and upstream != revision:
        raise FoundryError("Foundry snapshot revision does not match its source manifest")
    manifest = snapshot.get("system_manifest")
    if not isinstance(manifest, dict) or manifest.get("id") != "dnd5e":
        raise FoundryError("Invalid Foundry system manifest identity")
    return snapshot


def import_foundry_snapshot(path: Path, *, connection=None, imported_at: str | None = None) -> dict[str, Any]:
    """Import an already-acquired, immutable raw Foundry source snapshot."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    snapshot = _validate_snapshot(raw)
    content_sha = _content_hash(snapshot)
    declared = snapshot.get("content_sha256")
    if not isinstance(declared, str) or declared != content_sha:
        raise FoundryError("Foundry snapshot content SHA-256 mismatch")
    now = imported_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    own_connection = connection is None
    c = connection or connect()
    try:
        initialize(c)
        with c:
            existing = c.execute("SELECT id FROM sources WHERE id=?", (SOURCE_ID,)).fetchone()
            values = ("Foundry D&D5e SRD 5.2", "foundry_snapshot", "approved_supplement", AUTHORITY_ID,
                      REPRESENTATION_ID, "2024", 0, 1, "present", PROVIDER, "srd-5.2", 90,
                      "CC-BY-4.0", "https://creativecommons.org/licenses/by/4.0/", REPOSITORY)
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
                                (SOURCE_ID, f"foundry-{snapshot['upstream_revision'][:12]}", now, content_sha,
                                 f"{REPOSITORY}/tree/{snapshot['upstream_revision']}", str(path), snapshot["upstream_revision"]))
                version_id = cur.lastrowid
            c.execute("DELETE FROM evidence_chunks WHERE source_id=?", (SOURCE_ID,))
            c.execute("DELETE FROM content_records WHERE source_id=? AND source_version_id=?", (SOURCE_ID, version_id))
            diagnostics = _normalize(c, snapshot=snapshot, source_version_id=version_id, now=now)
            count = c.execute("SELECT count(*) FROM content_records WHERE source_id=? AND source_version_id=?",
                              (SOURCE_ID, version_id)).fetchone()[0]
    finally:
        if own_connection:
            c.close()
    return {"ok": True, "source_id": SOURCE_ID, "content_sha256": content_sha,
            "upstream_revision": snapshot["upstream_revision"], "content_records": count,
            "evidence_chunks": 0, "unchanged": unchanged, "diagnostics": diagnostics}


def rehydrate_foundry_imports(c, imported_at: str | None = None) -> dict[str, Any]:
    from .source import discover_source_manifests, sha256_file

    totals = {key: 0 for key in DIAGNOSTIC_KEYS}
    sources = records = 0
    for manifest in discover_source_manifests():
        if manifest.source_type != "foundry_snapshot":
            continue
        if sha256_file(manifest.content_path) != manifest.sha256:
            raise FoundryError(f"Stored Foundry snapshot hash mismatch: {manifest.id}")
        raw = json.loads(manifest.content_path.read_text(encoding="utf-8"))
        _validate_snapshot(raw, revision=manifest.upstream_revision)
        result = import_foundry_snapshot(manifest.content_path, connection=c, imported_at=imported_at)
        sources += 1
        records += result["content_records"]
        for key in totals:
            totals[key] += result["diagnostics"][key]
    return {"sources": sources, "content_records": records, "diagnostics": totals}
