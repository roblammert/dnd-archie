from pathlib import Path
import sqlite3

import yaml

from archie.db import SCHEMA, SCHEMA_VERSION
from archie.source import load_source_manifest


ROOT = Path(__file__).resolve().parents[1]


def test_schema_v5_adds_ingestion_provenance_without_replacing_legacy_fields():
    assert SCHEMA_VERSION == "5"
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

    assert (official.id, official.authority_type) == ("srd521", "official_srd")
    assert official.authority_id == "wotc:srd-5.2.1"
    assert official.representation_id == "wotc:official-srd-5.2.1"
    assert official.upstream_revision == "5.2.1"

    assert (open5e.id, open5e.authority_type) == ("open5e:srd-2024", "approved_supplement")
    assert open5e.authority_id == "wotc:srd-5.2.1"
    assert open5e.representation_id == "open5e:srd-2024"
    assert open5e.upstream_revision


def test_authority_declaration_lists_one_authority_and_required_representations():
    declaration = yaml.safe_load((ROOT / "sources/wotc-srd-5.2.1.yaml").read_text(encoding="utf-8"))
    assert declaration["authority"]["id"] == "wotc:srd-5.2.1"
    assert [item["id"] for item in declaration["representations"]] == [
        "wotc:official-srd-5.2.1",
        "open5e:srd-2024",
        "foundry:srd-5.2",
        "cantilux:dnd-srd-json",
    ]
