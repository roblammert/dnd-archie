from pathlib import Path
import sqlite3

import pytest
import yaml

from archie.db import SCHEMA, SCHEMA_VERSION
from archie.source import SourceIntegrityError, load_authority_declaration, load_source_manifest


ROOT = Path(__file__).resolve().parents[1]


def test_schema_v7_retains_alpha51_ingestion_provenance_fields():
    assert SCHEMA_VERSION == "7"
    c = sqlite3.connect(":memory:")
    try:
        c.executescript(SCHEMA)
        source_columns = {row[1] for row in c.execute("PRAGMA table_info(sources)")}
        version_columns = {row[1] for row in c.execute("PRAGMA table_info(source_versions)")}
        record_columns = {row[1] for row in c.execute("PRAGMA table_info(content_records)")}
    finally:
        c.close()

    assert {"id", "authority_type", "authority_id", "representation_id"} <= source_columns
    assert "upstream_revision" in version_columns
    assert {
        "authority_id",
        "representation_id",
        "upstream_id",
        "upstream_path",
        "normalization_schema_version",
    } <= record_columns
    assert "entity_key" not in record_columns


def test_committed_manifests_add_provenance_without_changing_legacy_identity():
    official = load_source_manifest(ROOT / "sources/srd521/source.yaml")
    open5e = load_source_manifest(ROOT / "sources/open5e/srd-2024/source.yaml")
    cantilux = load_source_manifest(ROOT / "sources/cantilux/dnd-srd-json/source.yaml")

    assert (official.id, official.authority_type) == ("srd521", "official_srd")
    assert official.authority_id == "wotc:srd-5.2.1"
    assert official.representation_id == "wotc:official-srd-5.2.1"
    assert official.upstream_revision == "5.2.1"

    assert (open5e.id, open5e.authority_type) == ("open5e:srd-2024", "approved_supplement")
    assert open5e.authority_id == "wotc:srd-5.2.1"
    assert open5e.representation_id == "open5e:srd-2024"
    assert open5e.upstream_revision

    assert (cantilux.id, cantilux.authority_type) == ("cantilux:dnd-srd-json", "approved_supplement")
    assert cantilux.authority_id == "wotc:srd-5.2.1"
    assert cantilux.representation_id == "cantilux:dnd-srd-json"
    assert cantilux.enabled is True
    assert len(cantilux.upstream_revision) == 40


def test_authority_declaration_lists_one_authority_and_required_representations():
    declaration = yaml.safe_load((ROOT / "sources/wotc-srd-5.2.1.yaml").read_text(encoding="utf-8"))
    assert declaration["authority"]["id"] == "wotc:srd-5.2.1"
    assert [item["id"] for item in declaration["representations"]] == [
        "wotc:official-srd-5.2.1",
        "open5e:srd-2024",
        "foundry:srd-5.2",
        "cantilux:dnd-srd-json",
    ]
    assert {item["id"]: item["source_id"] for item in declaration["representations"]} == {
        "wotc:official-srd-5.2.1": "srd521",
        "open5e:srd-2024": "open5e:srd-2024",
        "foundry:srd-5.2": "foundry:srd-5.2",
        "cantilux:dnd-srd-json": "cantilux:dnd-srd-json",
    }


@pytest.mark.parametrize("schema_version", [pytest.param("missing", id="missing"), None, True, 2, "1"])
def test_authority_declaration_rejects_unsupported_schema_version(tmp_path, schema_version):
    declaration = {
        "authority": {"id": "wotc:srd-5.2.1"},
        "representations": [
            {"id": "wotc:official-srd-5.2.1", "source_id": "srd521"},
        ],
    }
    if schema_version != "missing":
        declaration["schema_version"] = schema_version
    path = tmp_path / "authority.yaml"
    path.write_text(yaml.safe_dump(declaration), encoding="utf-8")

    with pytest.raises(SourceIntegrityError, match="unsupported schema_version.*expected 1"):
        load_authority_declaration(path)


def test_authority_declaration_accepts_schema_version_one(tmp_path):
    path = tmp_path / "authority.yaml"
    path.write_text(yaml.safe_dump({
        "schema_version": 1,
        "authority": {"id": "wotc:srd-5.2.1"},
        "representations": [
            {"id": "wotc:official-srd-5.2.1", "source_id": "srd521"},
        ],
    }), encoding="utf-8")

    assert load_authority_declaration(path) == {
        "wotc:srd-5.2.1": {"wotc:official-srd-5.2.1": "srd521"},
    }
