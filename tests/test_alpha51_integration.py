from dataclasses import replace
from pathlib import Path
import sqlite3

import pytest

from archie.db import SCHEMA, connect
from archie.ingest import ingest
from archie.source import (
    SourceIntegrityError,
    load_source_manifest,
    validate_content_authority,
    validate_manifest_authority,
    verify_manifest,
)
from archie.source_library import substantive_corpus_fingerprint


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_ID = "wotc:srd-5.2.1"
REPRESENTATIONS = {
    "wotc:official-srd-5.2.1",
    "open5e:srd-2024",
    "foundry:srd-5.2",
    "cantilux:dnd-srd-json",
}


def _memory_database():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


def test_two_clean_rebuilds_have_identical_substantive_corpus():
    first_ingest = ingest()
    first = substantive_corpus_fingerprint()
    second_ingest = ingest()
    second = substantive_corpus_fingerprint()

    assert first == second
    assert first["authority_ids"] == [AUTHORITY_ID]
    assert set(first["representation_ids"]) == REPRESENTATIONS
    assert first["records_by_representation"] == {
        "cantilux:dnd-srd-json": 2703,
        "foundry:srd-5.2": 2095,
        "open5e:srd-2024": 1740,
        "wotc:official-srd-5.2.1": 364,
    }
    assert first_ingest["corpus_authority"] == second_ingest["corpus_authority"]


def test_rebuilt_corpus_is_wotc_only_and_ingestion_only_representations_are_quarantined():
    ingest()
    c = connect()
    try:
        assert validate_content_authority(c) == {
            "content_records": 6902,
            "authority_ids": [AUTHORITY_ID],
            "representation_ids": sorted(REPRESENTATIONS),
        }
        states = {row["representation_id"]: dict(row) for row in c.execute(
            '''SELECT s.representation_id,s.enabled,count(DISTINCT cr.id) AS records,
                      count(DISTINCT ec.id) AS evidence
               FROM sources s LEFT JOIN content_records cr ON cr.source_id=s.id
               LEFT JOIN evidence_chunks ec ON ec.source_id=s.id
               GROUP BY s.representation_id,s.enabled''')}
        for representation, count in (("foundry:srd-5.2", 2095),
                                      ("cantilux:dnd-srd-json", 2703)):
            assert states[representation]["enabled"] == 0
            assert states[representation]["records"] == count
            assert states[representation]["evidence"] == 0
            fts = c.execute(
                '''SELECT count(*) FROM evidence_fts f JOIN evidence_chunks ec ON ec.id=f.rowid
                   JOIN sources s ON s.id=ec.source_id WHERE s.representation_id=?''',
                (representation,),
            ).fetchone()[0]
            assert fts == 0
    finally:
        c.close()


@pytest.mark.parametrize("name", ["Acid Arrow", "Aboleth", "Acid", "Advantage/Disadvantage"])
def test_cross_representation_records_coexist_without_overwrite(name):
    ingest()
    c = connect()
    try:
        rows = c.execute(
            '''SELECT cr.source_id,cr.representation_id,cr.upstream_id,cr.upstream_path,sv.id AS version_id
               FROM content_records cr JOIN source_versions sv ON sv.id=cr.source_version_id
               WHERE lower(cr.name)=lower(?) ORDER BY cr.representation_id''', (name,)
        ).fetchall()
        assert len({row["representation_id"] for row in rows}) >= 2
        assert len({(row["source_id"], row["upstream_id"], row["upstream_path"], row["version_id"])
                    for row in rows}) == len(rows)
    finally:
        c.close()


@pytest.mark.parametrize(("field", "value", "message"), [
    ("authority_id", None, "lacks authority_id"),
    ("authority_id", "unknown:authority", "Unknown authority_id"),
    ("representation_id", None, "lacks representation_id"),
    ("representation_id", "unknown:representation", "not declared"),
])
def test_malformed_manifest_authority_metadata_fails_closed(field, value, message):
    manifest = load_source_manifest(ROOT / "sources/srd521/source.yaml")
    with pytest.raises(SourceIntegrityError, match=message):
        validate_manifest_authority(replace(manifest, **{field: value}))


def test_changed_raw_snapshot_hash_fails_closed(tmp_path):
    original = load_source_manifest(ROOT / "sources/open5e/srd-2024/source.yaml")
    raw = tmp_path / "changed.json"
    raw.write_bytes(original.content_path.read_bytes() + b"\n")
    manifest_path = tmp_path / "source.yaml"
    manifest_path.write_text("placeholder", encoding="utf-8")
    changed = replace(original, filename=raw.name, manifest_path=manifest_path)
    with pytest.raises(SourceIntegrityError, match="SHA-256 mismatch"):
        verify_manifest(changed)


def test_rejected_or_mismatched_record_cannot_pass_corpus_validation():
    c = _memory_database()
    try:
        c.execute(
            '''INSERT INTO sources(id,name,source_type,authority_type,authority_id,representation_id,
               enabled,approved,license_status,priority,created_at,updated_at)
               VALUES('bad','Bad','fixture','approved_supplement',?,?,0,1,'present',1,'now','now')''',
            (AUTHORITY_ID, "open5e:srd-2024"),
        )
        version_id = c.execute(
            '''INSERT INTO source_versions(source_id,imported_at,content_sha256,active)
               VALUES('bad','now','hash',1)'''
        ).lastrowid
        c.execute(
            '''INSERT INTO content_records(source_id,source_version_id,content_type,authority_id,
               representation_id,structured_json,created_at)
               VALUES('bad',?,'rules',?,'foundry:srd-5.2','{}','now')''',
            (version_id, AUTHORITY_ID),
        )
        with pytest.raises(SourceIntegrityError, match="does not match source"):
            validate_content_authority(c)
        assert c.execute("SELECT count(*) FROM evidence_chunks").fetchone()[0] == 0
        assert c.execute("SELECT count(*) FROM evidence_fts").fetchone()[0] == 0
    finally:
        c.close()
