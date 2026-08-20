from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

import archie.cantilux as cantilux
from archie.cantilux import CantiluxError, cantilux_record_admission, import_cantilux_snapshot
from archie.db import SCHEMA
from archie.source import load_source_manifest
from archie import source_library


ROOT = Path(__file__).resolve().parents[1]
REVISION = cantilux.UPSTREAM_REVISION
RAW_PATH = ROOT / "sources/cantilux/dnd-srd-json/raw/cantilux-dnd-srd-json-df536fe94c92.json"


def _metadata(**changes):
    value = {
        "name": "dnd-srd-json", "srdVersion": "5.2.1", "rulesRevision": "2024",
        "officialSrdUrl": "https://www.dndbeyond.com/srd", "license": "CC-BY-4.0",
        "generatedAt": "fixture",
    }
    value.update(changes)
    return value


def _record(record_id="acid-arrow", collection="spells"):
    return {
        "id": record_id, "slug": record_id, "name": "Acid Arrow", "collection": collection,
        "source": {"documentId": "spells", "sectionId": "spells-acid-arrow",
                   "path": ["Spells", "Acid Arrow"]},
        "content": "Fixture spell text.", "text": "Fixture spell text.", "tables": [],
    }


def _snapshot(records=None, *, metadata=None):
    records = [_record()] if records is None else records
    identity = _metadata() if metadata is None else metadata
    collection = {"count": len(records),
                  "itemIds": [x.get("id") for x in records],
                  "items": [{"id": x.get("id"), "name": x.get("name"), "collection": "spells"}
                            for x in records],
                  "resources": records}
    identity["collections"] = {"spells": {"count": len(records), "itemIds": collection["itemIds"]}}
    return {
        "manifest": identity, "metadata": dict(identity),
        "documents": [{"id": "spells", "title": "Spells"}],
        "sections": [{"id": "spells-acid-arrow", "documentId": "spells"}],
        "collections": {"spells": collection},
    }


def _write(tmp_path, snapshot):
    path = tmp_path / "cantilux.json"
    path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
    return path


def _connection():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


@pytest.mark.parametrize(("record", "collection", "expected"), [
    (_record(), "spells", "accepted"),
    (_record(collection="third-party"), "spells", "invalid_provenance"),
    ({"id": "x", "collection": "spells"}, "spells", "invalid_provenance"),
    (_record(record_id=""), "spells", "invalid_provenance"),
])
def test_record_admission_requires_stable_identity_and_source_lineage(record, collection, expected):
    assert cantilux_record_admission(record, collection) == expected


def test_import_accepts_corpus_provenance_and_preserves_record_provenance(tmp_path):
    c = _connection()
    result = import_cantilux_snapshot(_write(tmp_path, _snapshot()), connection=c, imported_at="now")
    assert result["diagnostics"] == {"observed": 1, "accepted": 1, "rejected_non_wotc": 0,
                                     "invalid_provenance": 0, "normalization_failures": 0}
    row = c.execute("SELECT * FROM content_records WHERE source_id=?", (cantilux.SOURCE_ID,)).fetchone()
    assert (row["authority_id"], row["representation_id"]) == (cantilux.AUTHORITY_ID, cantilux.REPRESENTATION_ID)
    assert row["upstream_id"] == "acid-arrow"
    assert row["upstream_path"] == "data/resources/spells/acid-arrow.json"
    assert row["normalization_schema_version"] == 1
    version = c.execute("SELECT upstream_revision FROM source_versions WHERE source_id=?", (cantilux.SOURCE_ID,)).fetchone()
    assert version["upstream_revision"] == REVISION
    assert c.execute("SELECT count(*) FROM evidence_chunks WHERE source_id=?", (cantilux.SOURCE_ID,)).fetchone()[0] == 0
    assert c.execute("SELECT count(*) FROM evidence_fts").fetchone()[0] == 0
    c.close()


def test_changed_pinned_revision_fails_closed(tmp_path):
    with pytest.raises(CantiluxError, match="pinned upstream commit"):
        import_cantilux_snapshot(
            _write(tmp_path, _snapshot()), connection=_connection(),
            upstream_revision="a" * 40,
        )


@pytest.mark.parametrize(("key", "value"), [
    ("srdVersion", "5.1"), ("rulesRevision", "2014"),
    ("license", "OGL-1.0a"), ("name", "unexpected-corpus"),
])
def test_mismatched_corpus_provenance_fails_closed_without_records(tmp_path, key, value):
    c = _connection()
    bad = _metadata(**{key: value})
    with pytest.raises(CantiluxError, match="provenance mismatch"):
        import_cantilux_snapshot(_write(tmp_path, _snapshot(metadata=bad)), connection=c)
    assert c.execute("SELECT count(*) FROM content_records").fetchone()[0] == 0
    assert c.execute("SELECT count(*) FROM sources").fetchone()[0] == 0
    c.close()


def test_invalid_record_is_rejected_and_reimport_is_idempotent(tmp_path):
    c = _connection()
    invalid = _record("bad")
    del invalid["source"]["sectionId"]
    path = _write(tmp_path, _snapshot([_record(), invalid]))
    first = import_cantilux_snapshot(path, connection=c, imported_at="now")
    second = import_cantilux_snapshot(path, connection=c, imported_at="later")
    assert first["diagnostics"] == {"observed": 2, "accepted": 1, "rejected_non_wotc": 0,
                                     "invalid_provenance": 1, "normalization_failures": 0}
    assert second["unchanged"] is True
    assert c.execute("SELECT count(*) FROM source_versions WHERE source_id=?", (cantilux.SOURCE_ID,)).fetchone()[0] == 1
    assert c.execute("SELECT count(*) FROM content_records WHERE source_id=?", (cantilux.SOURCE_ID,)).fetchone()[0] == 1
    c.close()


def test_snapshot_builder_verifies_revision_and_preserves_canonical_bytes(monkeypatch, tmp_path):
    checkout = tmp_path / "checkout"
    source = checkout / "data/srd.json"
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps(_snapshot(), indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(cantilux, "_run_git", lambda *args, cwd=None: REVISION)
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    first = cantilux.write_cantilux_snapshot(checkout, first_path)
    second = cantilux.write_cantilux_snapshot(checkout, second_path)
    assert first_path.read_bytes() == second_path.read_bytes() == source.read_bytes()
    assert first["snapshot_sha256"] == second["snapshot_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert first["resources"] == 1


def _full_alias_context():
    snapshot = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    collection = snapshot["collections"][cantilux.AREA_EFFECT_COLLECTION]
    documents = {item["id"] for item in snapshot["documents"]}
    sections = {item["id"]: item for item in snapshot["sections"]}
    manifest_collection = snapshot["manifest"]["collections"][cantilux.AREA_EFFECT_COLLECTION]
    return collection, manifest_collection, documents, sections


@pytest.mark.parametrize("resource_id", sorted(cantilux.AREA_EFFECT_RESOURCE_IDS))
def test_six_pinned_area_effect_defects_are_corroborated_and_admitted(resource_id):
    collection, manifest_collection, documents, sections = _full_alias_context()
    record = next(item for item in collection["resources"] if item["id"] == resource_id)
    assert record["collection"] == "area-of-effects"
    assert cantilux_record_admission(
        record, "areas-of-effect", collection=collection,
        manifest_collection=manifest_collection, documents=documents, sections=sections,
    ) == "accepted"


def test_area_effect_defect_without_required_corroboration_is_rejected():
    collection, manifest_collection, documents, sections = _full_alias_context()
    record = next(item for item in collection["resources"] if item["id"] == "cone")
    incomplete = dict(collection)
    incomplete["items"] = [item for item in collection["items"] if item["id"] != "cone"]
    assert cantilux_record_admission(
        record, "areas-of-effect", collection=incomplete,
        manifest_collection=manifest_collection, documents=documents, sections=sections,
    ) == "invalid_provenance"


@pytest.mark.parametrize("internal_collection", ["area-of-effects", "spell"])
def test_area_effect_spelling_mismatch_is_not_a_general_alias(internal_collection):
    collection, manifest_collection, documents, sections = _full_alias_context()
    record = dict(next(item for item in collection["resources"] if item["id"] == "cone"))
    record["collection"] = internal_collection
    assert cantilux_record_admission(
        record, "spells", collection=collection,
        manifest_collection=manifest_collection, documents=documents, sections=sections,
    ) == "invalid_provenance"


def test_committed_manifest_and_full_bundle_are_pinned_complete(monkeypatch):
    manifest = load_source_manifest(ROOT / "sources/cantilux/dnd-srd-json/source.yaml")
    assert (manifest.id, manifest.authority_id, manifest.representation_id) == (
        cantilux.SOURCE_ID, cantilux.AUTHORITY_ID, cantilux.REPRESENTATION_ID)
    assert manifest.upstream_revision == REVISION
    assert manifest.enabled is True and manifest.approved is True
    assert hashlib.sha256(RAW_PATH.read_bytes()).hexdigest() == manifest.sha256

    c = _connection()
    first = import_cantilux_snapshot(RAW_PATH, connection=c, imported_at="now")
    second = import_cantilux_snapshot(RAW_PATH, connection=c, imported_at="later")
    expected = {"observed": 2703, "accepted": 2703, "rejected_non_wotc": 0,
                "invalid_provenance": 0, "normalization_failures": 0}
    assert first["diagnostics"] == second["diagnostics"] == expected
    assert first["records_by_collection"] == second["records_by_collection"]
    assert (first["documents"], first["sections"], first["collections"]) == (13, 2876, 20)
    assert second["unchanged"] is True
    assert c.execute("SELECT count(*) FROM content_records WHERE source_id=?", (cantilux.SOURCE_ID,)).fetchone()[0] == 2703
    alias = c.execute("SELECT content_type,upstream_path,structured_json FROM content_records WHERE source_id=? AND upstream_id='cone'",
                      (cantilux.SOURCE_ID,)).fetchone()
    assert alias["content_type"] == "areas-of-effect"
    assert alias["upstream_path"] == "data/resources/areas-of-effect/cone.json"
    assert json.loads(alias["structured_json"])["collection"] == "area-of-effects"
    assert c.execute("SELECT count(*) FROM evidence_chunks WHERE source_id=?", (cantilux.SOURCE_ID,)).fetchone()[0] == 0
    assert c.execute("SELECT count(*) FROM evidence_fts").fetchone()[0] == 0
    c.close()

    monkeypatch.setattr("archie.source.discover_source_manifests", lambda: [manifest])
    rebuilt = _connection()
    restored = cantilux.rehydrate_cantilux_imports(rebuilt, "rebuild")
    assert restored["content_records"] == 2703
    assert restored["diagnostics"] == expected
    assert rebuilt.execute("SELECT count(*) FROM evidence_chunks").fetchone()[0] == 0
    assert rebuilt.execute("SELECT count(*) FROM evidence_fts").fetchone()[0] == 0
    rebuilt.close()


def test_cantilux_manifest_is_enabled_for_alpha63():
    assert load_source_manifest(ROOT / "sources/cantilux/dnd-srd-json/source.yaml").enabled is True
