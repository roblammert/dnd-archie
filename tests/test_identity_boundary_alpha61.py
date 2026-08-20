import json
import sqlite3

from archie.identity import build_identity, identity_fingerprint
from test_identity_alpha61 import database


def feature(entity_type, name, path, *, parent=None, parent_class="Wizard", level=None, source_path=None):
    content_type = "class-features" if entity_type == "class_feature" else "subclass-features"
    data = {"collection": content_type, "level": level, "source": {"path": source_path or []}}
    if entity_type == "class_feature":
        data["class"] = {"name": parent} if parent else None
    else:
        data["class"] = {"name": parent_class} if parent_class else None
        data["subclass"] = {"name": parent} if parent else None
    return ("cantilux:dnd-srd-json", content_type, name, path, data)


def test_feature_key_separates_parent_level_and_class_vs_subclass():
    c = database([
        feature("class_feature", "Shared Feature", "a", parent="Wizard", level=1),
        feature("class_feature", "Shared Feature", "b", parent="Wizard", level=2),
        feature("class_feature", "Shared Feature", "c", parent="Fighter", level=1),
        feature("subclass_feature", "Shared Feature", "d", parent="Evoker", level=1),
    ])
    build_identity(c)
    keys = {r[0] for r in c.execute("SELECT entity_type || ':' || canonical_key FROM canonical_entities")}
    assert keys == {"class_feature:wizard/1/shared-feature", "class_feature:wizard/2/shared-feature",
                    "class_feature:fighter/1/shared-feature", "subclass_feature:wizard/evoker/1/shared-feature"}


def test_missing_or_contradictory_feature_context_fails_closed():
    c = database([
        feature("class_feature", "Arcane Recovery", "a", level=1),
        feature("class_feature", "Arcane Recovery", "b", parent="Wizard"),
        feature("class_feature", "Arcane Recovery", "c", parent="Wizard", level=1,
                source_path=["Classes", "Fighter", "Level 1: Arcane Recovery"]),
        feature("subclass_feature", "Empowered Evocation", "d", parent="Evoker", parent_class=None, level=10),
    ])
    build_identity(c)
    assert [r[0] for r in c.execute("SELECT status FROM entity_mappings ORDER BY content_record_id")] == ["unmapped"] * 4


def test_collision_result_and_fingerprint_ignore_input_order():
    rows = [
        ("open5e:srd-2024", "spells", "Fireball", "spells/a", {}),
        ("open5e:srd-2024", "spells", "Fireball", "spells/b", {}),
        ("cantilux:dnd-srd-json", "spells", "Fireball", "spells/c", {"collection": "spells"}),
    ]
    fingerprints = []
    details = []
    for ordered in (rows, list(reversed(rows))):
        c = database(ordered)
        report = build_identity(c)
        assert report["collisions"] == 1
        assert {r[0] for r in c.execute("SELECT status FROM entity_mappings")} == {"ambiguous"}
        assert c.execute("SELECT count(*) FROM canonical_entities").fetchone()[0] == 0
        fingerprints.append(identity_fingerprint(c)["sha256"])
        details.append(sorted(r[0] for r in c.execute("SELECT detail_json FROM entity_mappings")))
    assert fingerprints[0] == fingerprints[1]
    assert details[0] == details[1]


def test_foundry_helper_actors_never_receive_entities():
    rows = [
        ("foundry:srd-5.2", "npc", "Arcane Eye", "packs/_source/actors24/conjurations/arcane-eye.yml", {}),
        ("foundry:srd-5.2", "npc", "Dancing Sword", "packs/_source/actors24/magic-items/dancing-sword.yml", {}),
        ("foundry:srd-5.2", "npc", "Otherworldly Steed", "packs/_source/actors24/companions/steed.yml", {}),
    ]
    c = database(rows)
    build_identity(c)
    assert c.execute("SELECT count(*) FROM canonical_entities").fetchone()[0] == 0
    assert {r[0] for r in c.execute("SELECT status FROM entity_mappings")} == {"unmapped"}


def test_database_rejects_impossible_status_method_identity_combinations():
    c = database([("open5e:srd-2024", "spells", "Fireball", "spells/fireball", {})])
    build_identity(c)
    with c:
        c.execute("DELETE FROM entity_mappings")
    invalid = [
        (None, "mapped", "semantic_key"),
        ("wotc:srd-5.2.1/spell/fireball", "unmapped", "none"),
        ("wotc:srd-5.2.1/spell/fireball", "ambiguous", "none"),
        ("wotc:srd-5.2.1/spell/fireball", "mapped", "none"),
    ]
    for entity_id, status, method in invalid:
        with __import__("pytest").raises(sqlite3.IntegrityError):
            c.execute("""INSERT INTO entity_mappings(content_record_id,canonical_entity_id,status,method,mapping_version)
                         VALUES(1,?,?,?,'test')""", (entity_id, status, method))
