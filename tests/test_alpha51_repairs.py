from dataclasses import replace
from pathlib import Path
import sqlite3

import pytest

from archie import source_library
from archie.db import SCHEMA, connect
from archie.ingest import ingest
from archie.open5e import rehydrate_open5e_imports
from archie.source import SourceIntegrityError, load_source_manifest
from archie.source_library import substantive_corpus_fingerprint


QUARANTINED = (
    ("foundry:srd-5.2", "sources/foundry/srd-5.2/source.yaml"),
    ("cantilux:dnd-srd-json", "sources/cantilux/dnd-srd-json/source.yaml"),
)


@pytest.mark.parametrize(("source_id", "manifest_path"), QUARANTINED)
@pytest.mark.parametrize(("changes", "message"), [
    ({"representation_id": None}, "lacks representation_id"),
    ({"representation_id": "open5e:srd-2024"}, "cannot claim representation"),
    ({"representation_id": "wotc:official-srd-5.2.1"}, "cannot claim representation"),
    ({"authority_id": None}, "lacks authority_id"),
    ({"authority_id": "unknown:authority"}, "Unknown authority_id"),
    ({"id": "contradictory:source"}, "cannot claim representation"),
])
def test_invalid_representation_enablement_fails_before_any_state_change(
        monkeypatch, source_id, manifest_path, changes, message):
    manifest = replace(load_source_manifest(Path(manifest_path)), **changes)
    raw = {
        "id": manifest.id,
        "representation_id": manifest.representation_id,
        "authority_id": manifest.authority_id,
        "approved": True,
        "license_status": "present",
        "license_name": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "edition": "2024",
    }
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    c.execute(
        '''INSERT INTO sources(id,name,source_type,authority_type,authority_id,representation_id,
           edition,enabled,approved,license_status,priority,created_at,updated_at)
           VALUES(?,?,?,?,?,?,?,0,1,'present',1,'now','now')''',
        (source_id, "Quarantined", "fixture", "approved_supplement",
         "wotc:srd-5.2.1", source_id, "2024"),
    )
    c.commit()
    materialized = []
    monkeypatch.setattr(source_library, "get_source_manifest", lambda requested: manifest)
    monkeypatch.setattr(source_library, "_manifest_data", lambda requested: (manifest.manifest_path, raw))
    monkeypatch.setattr(source_library, "connect", lambda: c)
    monkeypatch.setattr(source_library, "materialize_structured_evidence", materialized.append)

    with pytest.raises((SourceIntegrityError, ValueError), match=message):
        source_library.enable_source(source_id)

    assert materialized == []
    assert c.execute("SELECT enabled FROM sources WHERE id=?", (source_id,)).fetchone()[0] == 0
    assert c.execute("SELECT count(*) FROM evidence_chunks").fetchone()[0] == 0
    assert c.execute("SELECT count(*) FROM evidence_fts").fetchone()[0] == 0
    c.close()


def test_open5e_rehydration_is_repeat_idempotent():
    ingest()
    c = connect()
    try:
        before = substantive_corpus_fingerprint(c)
        first = rehydrate_open5e_imports(c, "repair-repeat")
        middle = substantive_corpus_fingerprint(c)
        second = rehydrate_open5e_imports(c, "repair-repeat")
        after = substantive_corpus_fingerprint(c)
        state = c.execute(
            '''SELECT (SELECT count(*) FROM sources WHERE id='open5e:srd-2024') AS sources,
                      (SELECT count(*) FROM source_versions WHERE source_id='open5e:srd-2024' AND active=1) AS active_versions,
                      (SELECT count(*) FROM source_versions WHERE source_id='open5e:srd-2024') AS versions,
                      (SELECT count(*) FROM content_records WHERE source_id='open5e:srd-2024') AS records,
                      (SELECT count(*) FROM evidence_chunks WHERE source_id='open5e:srd-2024') AS evidence'''
        ).fetchone()
    finally:
        c.close()

    assert first == second
    assert before == middle == after
    assert dict(state) == {
        "sources": 1,
        "active_versions": 1,
        "versions": 1,
        "records": 1740,
        "evidence": 2896,
    }
