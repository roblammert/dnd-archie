import json
import sqlite3

import pytest

from archie.db import SCHEMA
from archie.identity import (build_identity, canonical_entity_id, identity_fingerprint,
                             normalize_key, observation_from_record, select_mapping_method)


def database(rows):
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    c.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              ("x", "x", "structured", "official_srd", "wotc:srd-5.2.1", "open5e:srd-2024", "2024", 0, 1, "present", "x", "x", 1, None, None, None, "x", "x"))
    c.execute("INSERT INTO source_versions VALUES (1,'x','1','x','hash',NULL,NULL,NULL,1)")
    for i, row in enumerate(rows, 1):
        rep, typ, name, path, data = row
        c.execute("""INSERT INTO content_records(id,source_id,source_version_id,content_type,name,authority_id,representation_id,upstream_id,upstream_path,structured_json,created_at)
                     VALUES(?,'x',1,?,?, 'wotc:srd-5.2.1',?,?,?,?,'x')""",
                  (i, typ, name, rep, path, path, json.dumps(data)))
    return c


def test_canonical_normalization_is_narrow_and_ids_are_readable():
    assert normalize_key("Mage’s—Hand") == "mage's-hand"
    assert normalize_key("Elf, Drow") == "elf-drow"
    assert normalize_key("Elf, High") != normalize_key("Elf, Wood")
    assert normalize_key("Level 10") == "level-10"
    assert canonical_entity_id("class_feature", "wizard/1/arcane-recovery") == \
        "wotc:srd-5.2.1/class-feature/wizard/1/arcane-recovery"


def test_mapping_precedence_is_locked():
    assert select_mapping_method(structural_id=True, explicit_crosswalk=True, semantic_key=True) == "structural_id"
    assert select_mapping_method(explicit_crosswalk=True, semantic_key=True, reviewed_alias=True) == "explicit_crosswalk"
    assert select_mapping_method(semantic_key=True, reviewed_alias=True) == "semantic_key"
    assert select_mapping_method(reviewed_alias=True, singleton=True) == "reviewed_alias"
    assert select_mapping_method(singleton=True) == "singleton"


def test_incompatible_types_and_variants_do_not_merge():
    c = database([
        ("open5e:srd-2024", "spells", "Resistance", "spells/resistance", {}),
        ("cantilux:dnd-srd-json", "rules", "Resistance", "rules/resistance", {"collection": "rules"}),
        ("open5e:srd-2024", "species", "Elf", "species/elf", {}),
        ("foundry:srd-5.2", "race", "Elf, Drow", "packs/_source/origins24/species/elf-drow.yml", {}),
    ])
    build_identity(c)
    ids = {r[0] for r in c.execute("SELECT id FROM canonical_entities")}
    assert "wotc:srd-5.2.1/spell/resistance" in ids
    assert "wotc:srd-5.2.1/rule/resistance" in ids
    assert "wotc:srd-5.2.1/species/elf" in ids
    assert "wotc:srd-5.2.1/species/elf-drow" in ids


def test_feature_identity_requires_parent_level_and_name():
    full = {"collection": "class-features", "class": {"name": "Wizard"}, "level": 1}
    missing = {"collection": "class-features", "class": {"name": "Wizard"}}
    c = database([
        ("cantilux:dnd-srd-json", "class-features", "Level 1: Arcane Recovery", "a", full),
        ("cantilux:dnd-srd-json", "class-features", "Arcane Recovery", "b", missing),
    ])
    build_identity(c)
    rows = list(c.execute("SELECT status,mapping_key FROM entity_mappings ORDER BY content_record_id"))
    assert tuple(rows[0]) == ("mapped", "wizard/1/arcane-recovery")
    assert tuple(rows[1]) == ("unmapped", None)


def test_same_name_features_under_different_parents_are_separate():
    c = database([
        ("cantilux:dnd-srd-json", "class-features", "Level 4: Ability Score Improvement", "a", {"collection":"class-features","class":{"name":"Wizard"},"level":4}),
        ("cantilux:dnd-srd-json", "class-features", "Level 4: Ability Score Improvement", "b", {"collection":"class-features","class":{"name":"Fighter"},"level":4}),
    ])
    build_identity(c)
    assert c.execute("SELECT count(*) FROM canonical_entities").fetchone()[0] == 2


def test_collision_is_ambiguous_and_unmerged():
    c = database([
        ("open5e:srd-2024", "spells", "Fireball", "spells/a", {}),
        ("open5e:srd-2024", "spells", "Fireball", "spells/b", {}),
    ])
    report = build_identity(c)
    assert report["collisions"] == 1
    assert c.execute("SELECT count(*) FROM canonical_entities").fetchone()[0] == 0
    assert {r[0] for r in c.execute("SELECT status FROM entity_mappings")} == {"ambiguous"}


def test_singleton_unknown_and_persistence_are_deterministic():
    rows = [("open5e:srd-2024", "spells", "Fireball", "spells/fireball", {}),
            ("open5e:srd-2024", "rules", "Mystery", "rules/mystery", {})]
    a = database(rows); build_identity(a)
    b = database(list(reversed(rows))); build_identity(b)
    assert identity_fingerprint(a)["sha256"] == identity_fingerprint(b)["sha256"]
    assert a.execute("SELECT method FROM entity_mappings WHERE status='mapped'").fetchone()[0] == "singleton"
    assert a.execute("SELECT status FROM entity_mappings WHERE method='none'").fetchone()[0] == "unmapped"


def test_pdf_is_absent_from_mapping_relation():
    c = database([("wotc:official-srd-5.2.1", "page", "PDF page 1", "x#page=1", {})])
    build_identity(c)
    assert c.execute("SELECT count(*) FROM entity_mappings").fetchone()[0] == 0
