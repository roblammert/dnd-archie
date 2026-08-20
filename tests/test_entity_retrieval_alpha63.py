from dataclasses import replace
import shutil
import pytest

from archie import db as db_module
from archie import retrieve as retrieve_module
from archie.config import settings
from archie.db import connect
from archie.evidence_families import set_representation_searchable
from archie.provenance import source_usage
from archie.retrieve import (_family_aware_select, build_query_plan,
                             detect_evidence_conflicts, search, Evidence)
from archie.source_library import retrieval_activation_fingerprint


def _item(eid, family, entity, score, *, representation="open5e:srd-2024",
          kind="structured_record", family_type="entity_summary", semantic_key="summary"):
    return ({"id": eid, "evidence_id": eid, "family_id": family,
             "canonical_entity_id": entity, "representation_id": representation,
             "evidence_kind": kind, "normalized_digest": eid,
             "family_type": family_type, "semantic_key": semantic_key,
             "conflict_status": "clear", "page_pdf": None, "record_name": eid,
             "text": eid}, score, ["broad"])


def test_family_score_is_best_member_and_duplicate_consumes_one_slot():
    ranked = [
        _item("a1", "family-a", "entity-a", 10),
        _item("a2", "family-a", "entity-a", 10),
        _item("b1", "family-b", "entity-b", 11),
    ]
    selected = _family_aware_select(ranked, build_query_plan("general query"), 2)
    assert [item[0]["family_id"] for item in selected] == ["family-b", "family-a"]


@pytest.mark.parametrize("kind,family_type", (
    ("structured_record", "field"),       # spell field
    ("structured_record", "field"),       # monster field
    ("table", "field"),                   # equipment field
    ("prose", "prose_rule"),              # explanatory prose
))
def test_three_representations_never_amplify_a_family_over_one_better_result(kind, family_type):
    repeated = [
        _item(f"same-{index}", "same-family", "same-entity", 4,
              representation=representation, kind=kind, family_type=family_type)
        for index, representation in enumerate(
            ("open5e:srd-2024", "foundry:srd-5.2", "cantilux:dnd-srd-json")
        )
    ]
    better = _item("better", "better-family", "better-entity", 5,
                   kind=kind, family_type=family_type)
    selected = _family_aware_select(repeated + [better], build_query_plan("general query"), 1)
    assert selected[0][0]["family_id"] == "better-family"  # summed behavior would choose 12 over 5


def test_right_evidence_kind_beats_provider_with_higher_member_score():
    ranked = [
        _item("prose", "family", "entity", 20, representation="foundry:srd-5.2", kind="prose"),
        _item("field", "family", "entity", 10, representation="cantilux:dnd-srd-json", kind="structured_field"),
    ]
    selected = _family_aware_select(ranked, build_query_plan("What is its range?"), 1)
    assert selected[0][0]["evidence_id"] == "field"
    assert selected[0][1] == 20


def test_same_kind_member_selection_prefers_compact_packet_before_provider():
    ranked = [
        _item("long", "family", "entity", 20, representation="cantilux:dnd-srd-json", kind="prose"),
        _item("short", "family", "entity", 10, representation="foundry:srd-5.2", kind="prose"),
    ]
    ranked[0][0]["text"] = "x" * 1000
    ranked[1][0]["text"] = "x" * 100
    selected = _family_aware_select(ranked, build_query_plan("explain it"), 1)
    assert selected[0][0]["evidence_id"] == "short"


def test_entity_budget_preserves_an_alternative_entity():
    ranked = [_item(f"a{i}", f"fa{i}", "entity-a", 20-i) for i in range(5)]
    ranked.append(_item("b", "fb", "entity-b", 1))
    selected = _family_aware_select(ranked, build_query_plan("general query"), 4)
    assert "entity-b" in {item[0]["canonical_entity_id"] for item in selected}


def test_real_field_intent_and_conflict_gate():
    fireball = search("Fireball range", top_k=3, expand_neighbors=False)
    assert fireball[0].evidence_family_id.endswith("/spell/fireball/field/range")
    dart = search("Dart weight", top_k=3, expand_neighbors=False)
    conflicts = detect_evidence_conflicts(dart)
    assert conflicts[0]["evidence_family_id"].endswith("/equipment/dart/field/weight")
    assert len(conflicts[0]["source_ids"]) == 3  # disagreement is reported, never voted
    awaken_school = search("Awaken school", top_k=5, expand_neighbors=False)
    assert not detect_evidence_conflicts(awaken_school)
    assert awaken_school[0].evidence_family_id.endswith("/spell/awaken/field/school")


def test_conflicted_field_does_not_poison_unrelated_same_name_or_feature_queries():
    for query in ("Light rules", "Bestow Curse spell", "Sorcerer Metamagic feature"):
        assert not detect_evidence_conflicts(search(query, top_k=5, expand_neighbors=False))


def test_magic_item_generic_and_explicit_enhancement_variants_rank_exactly():
    generic = search("Adamantine Armor", top_k=5, expand_neighbors=False)
    assert generic[0].canonical_entity_id == "wotc:srd-5.2.1/magic-item/adamantine-armor"
    assert len({item.canonical_entity_id for item in generic}) == len(generic)
    for modifier in (1, 2, 3):
        items = search(f"Ammunition +{modifier}", top_k=5, expand_neighbors=False)
        assert items[0].canonical_entity_id == f"wotc:srd-5.2.1/magic-item/ammunition-{modifier}"
    plate = search("Adamantine Armor Plate", top_k=5, expand_neighbors=False)
    assert plate[0].canonical_entity_id == "wotc:srd-5.2.1/magic-item/adamantine-armor-plate"


def test_field_feature_table_and_variant_intents_target_the_requested_kind():
    assert search("Aboleth armor class", 5, expand_neighbors=False)[0].evidence_family_id.endswith("/monster/aboleth/field/armor-class")
    assert search("Aboleth hit points", 5, expand_neighbors=False)[0].evidence_family_id.endswith("/monster/aboleth/field/hit-points")
    assert search("Sorcerer features", 5, expand_neighbors=False)[0].evidence_family_id.startswith(
        "wotc:srd-5.2.1/class-feature/sorcerer/")
    assert search("equipment table", 5, expand_neighbors=False)[0].evidence_kind == "table"
    assert search("High Elf", 5, expand_neighbors=False)[0].canonical_entity_id == "wotc:srd-5.2.1/species/elf-high"


def test_all_representations_are_one_internal_authority():
    evidence = search("explain Fireball", top_k=5, expand_neighbors=False)
    assert {item.authority_id for item in evidence} == {"wotc:srd-5.2.1"}
    mode, uses = source_usage(evidence, None)
    assert mode == "official_only"
    assert len(uses) == 1
    assert uses[0].source_id == "wotc:srd-5.2.1"
    assert uses[0].representation_ids


@pytest.mark.parametrize("representations", (
    ("foundry:srd-5.2",),
    ("cantilux:dnd-srd-json",),
    ("foundry:srd-5.2", "open5e:srd-2024"),
    ("wotc:official-srd-5.2.1", "cantilux:dnd-srd-json"),
))
def test_player_provenance_collapses_representation_combinations_to_one_authority(representations):
    evidence = [Evidence(f"E-{index}", None, None, "Test", "Test", 1,
                         source_id=representation, authority_id="wotc:srd-5.2.1",
                         representation_id=representation)
                for index, representation in enumerate(representations)]
    mode, uses = source_usage(evidence, [{"evidence_ids": [e.evidence_id for e in evidence]}])
    assert mode == "official_only"
    assert len(uses) == 1 and uses[0].source_id == "wotc:srd-5.2.1"
    assert set(uses[0].representation_ids) == set(representations)


@pytest.mark.parametrize("source_id,expected", (
    ("foundry:srd-5.2", 1817),
    ("cantilux:dnd-srd-json", 3435),
))
def test_activation_is_reversible_idempotent_and_keeps_ambiguous_quarantined(source_id, expected):
    c = connect()
    try:
        c.execute("BEGIN")
        before_ids = [r[0] for r in c.execute(
            "SELECT evidence_id FROM evidence_chunks WHERE source_id=? ORDER BY evidence_id", (source_id,))]
        before_members = c.execute('''SELECT count(*) FROM evidence_family_members m
                                      JOIN evidence_chunks ec ON ec.id=m.evidence_chunk_id
                                      WHERE ec.source_id=?''', (source_id,)).fetchone()[0]
        assert set_representation_searchable(c, source_id, False) == 0
        assert c.execute('''SELECT count(DISTINCT v.doc) FROM evidence_fts_vocab v
                            JOIN evidence_chunks ec ON ec.id=v.doc WHERE ec.source_id=?''', (source_id,)).fetchone()[0] == 0
        first = set_representation_searchable(c, source_id, True)
        second = set_representation_searchable(c, source_id, True)
        assert first == second == expected
        assert before_ids == [r[0] for r in c.execute(
            "SELECT evidence_id FROM evidence_chunks WHERE source_id=? ORDER BY evidence_id", (source_id,))]
        assert before_members == c.execute('''SELECT count(*) FROM evidence_family_members m
                                              JOIN evidence_chunks ec ON ec.id=m.evidence_chunk_id
                                              WHERE ec.source_id=?''', (source_id,)).fetchone()[0]
        assert c.execute('''SELECT count(DISTINCT v.doc) FROM evidence_fts_vocab v
                            JOIN evidence_chunks ec ON ec.id=v.doc WHERE ec.source_id=?''', (source_id,)).fetchone()[0] == expected
        assert c.execute('''SELECT count(*) FROM evidence_chunks ec
                            JOIN entity_mappings em ON em.content_record_id=ec.content_record_id
                            WHERE ec.source_id=? AND em.status='ambiguous'
                              AND ec.searchable=1''', (source_id,)).fetchone()[0] == 0
    finally:
        c.rollback()
        c.close()


def test_activation_fingerprint_is_deterministic():
    assert retrieval_activation_fingerprint() == retrieval_activation_fingerprint()


def test_ambiguous_evidence_is_quarantined_across_all_structured_representations():
    c = connect()
    try:
        assert c.execute('''SELECT count(DISTINCT ec.id) FROM evidence_chunks ec
                            JOIN entity_mappings em ON em.content_record_id=ec.content_record_id
                            WHERE em.status='ambiguous' AND ec.searchable=1''').fetchone()[0] == 0
    finally:
        c.close()
    acid = search("Acid cost", top_k=5, expand_neighbors=False)
    assert all(item.record_name != "Acid" for item in acid)


def test_class_focus_and_multi_entity_queries_are_bounded_but_retain_targets():
    druid = search("Druid", top_k=5, expand_neighbors=False)
    assert {item.canonical_entity_id for item in druid} == {"wotc:srd-5.2.1/class/druid"}
    assert sum(item.evidence_kind == "table" for item in druid) <= 2
    assert any(item.evidence_kind == "prose" for item in druid)
    multiple = search("Druid and Sorcerer", top_k=5, expand_neighbors=False)
    entities = {item.canonical_entity_id for item in multiple}
    assert "wotc:srd-5.2.1/class/druid" in entities
    assert "wotc:srd-5.2.1/class/sorcerer" in entities


def test_live_x_y_y_y_family_conflict_never_votes(monkeypatch, tmp_path):
    database = tmp_path / "archie.sqlite3"
    shutil.copy2(settings.database, database)
    local_settings = replace(settings, database=database)
    monkeypatch.setattr(db_module, "settings", local_settings)
    monkeypatch.setattr(retrieve_module, "settings", local_settings)
    c = db_module.connect()
    try:
        family = "wotc:srd-5.2.1/rule/quorumstone/field/potency"
        c.execute("""INSERT INTO evidence_families
                     (id,authority_id,canonical_entity_id,family_type,semantic_key,conflict_status,selection_version)
                     VALUES(?, 'wotc:srd-5.2.1', NULL, 'field', 'potency', 'conflicted', 'test')""", (family,))
        values = ("X", "Y", "Y", "Y")
        sources = ("srd521", "open5e:srd-2024", "foundry:srd-5.2", "cantilux:dnd-srd-json")
        for index, (source, value) in enumerate(zip(sources, values)):
            version = c.execute("SELECT id FROM source_versions WHERE source_id=? AND active=1", (source,)).fetchone()[0]
            evidence_id = f"QUORUM-{index}"
            chunk = c.execute("""INSERT INTO evidence_chunks
                (evidence_id,source_id,source_version_id,heading,text,evidence_kind,searchable)
                VALUES(?,?,?,'Quorumstone','Quorumstone potency value','structured_field',1)""",
                (evidence_id, source, version)).lastrowid
            representation = c.execute("SELECT representation_id FROM sources WHERE id=?", (source,)).fetchone()[0]
            c.execute("""INSERT INTO evidence_family_members
                (family_id,evidence_chunk_id,representation_id,evidence_role,normalized_digest)
                VALUES(?,?,?,'observation',?)""", (family, chunk, representation, f"digest-{index}"))
            c.execute("""INSERT INTO evidence_facts
                (id,family_id,evidence_chunk_id,field_key,canonical_value,display_value,value_schema_version)
                VALUES(?,?,?,?,?,?, 'test')""", (f"fact-{index}", family, chunk, "potency", value, value))
        c.commit()
    finally:
        c.close()
    items = retrieve_module.search("Quorumstone potency", top_k=3, expand_neighbors=False)
    conflicts = retrieve_module.detect_evidence_conflicts(items)
    assert conflicts[0]["evidence_family_id"] == family
    assert len(conflicts[0]["source_ids"]) == 4


@pytest.mark.parametrize("query", (
    "Fireball range", "Attack", "Awaken casting time",
    "What happens when I have advantage on a roll?",
))
@pytest.mark.parametrize("top_k", (1, 3, 5, 10))
def test_top_k_budgets_primary_families_with_bounded_pdf_neighbors(query, top_k):
    items = search(query, top_k=top_k)
    primary = [item for item in items if item.origin == "primary"]
    assert len(primary) <= top_k
    assert len({item.evidence_family_id or item.evidence_id for item in primary}) == len(primary)
    assert len(items) <= top_k + 6  # at most two neighbors around three PDF primaries
