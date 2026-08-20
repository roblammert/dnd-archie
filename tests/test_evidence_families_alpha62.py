import sqlite3

from archie.db import SCHEMA, connect
from archie.evidence_families import (_finalize_member_roles, evidence_fingerprint, family_id,
                                     normalize_evidence, normalized_digest, refresh_conflicts)
from archie.evidence_selection import rank_evidence
from archie.identity import identity_fingerprint
from archie.source_library import substantive_corpus_fingerprint
from archie.structured_facts import FIELD_ALLOWLIST, canonicalize_field


FROZEN_ALPHA51 = "1ee9f26b61a32f74dade72116dff397109c49f859f2bd04386553128f9b7b27f"
FROZEN_ALPHA61 = "0f096b45de75264a31b1746981c9ea92f21a6a51973dd2534c63778ccc18825a"


def test_family_ids_are_deterministic_readable_and_scoped():
    expected = "wotc:srd-5.2.1/spell/fireball/field/range"
    assert family_id("wotc:srd-5.2.1", "spell/fireball", "field", "Range") == expected
    assert family_id("wotc:srd-5.2.1", "spell/fireball", "field", "Range") == expected
    assert family_id("wotc:srd-5.2.1", "rule/resistance", "prose_rule", "description") != \
           family_id("wotc:srd-5.2.1", "spell/resistance", "prose_rule", "description")


def test_searchable_gate_handles_insert_update_and_delete():
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA)
    c.execute("INSERT INTO sources(id,name,source_type,authority_type,created_at,updated_at) VALUES('s','s','x','official_srd','n','n')")
    version = c.execute("INSERT INTO source_versions(source_id,content_sha256,imported_at) VALUES('s','x','n')").lastrowid
    c.execute("INSERT INTO evidence_chunks(evidence_id,source_id,source_version_id,heading,text,searchable) VALUES('Q','s',?,'Fireball','quarantine token',0)", (version,))
    assert c.execute("SELECT count(*) FROM evidence_fts_vocab").fetchone()[0] == 0
    c.execute("UPDATE evidence_chunks SET heading='Still quarantined' WHERE evidence_id='Q'")
    assert c.execute("SELECT count(*) FROM evidence_fts_vocab").fetchone()[0] == 0
    c.execute("UPDATE evidence_chunks SET searchable=1 WHERE evidence_id='Q'")
    assert c.execute("SELECT count(*) FROM evidence_fts WHERE evidence_fts MATCH 'quarantine'").fetchone()[0] == 1
    c.execute("UPDATE evidence_chunks SET text='replacement token' WHERE evidence_id='Q'")
    assert c.execute("SELECT count(*) FROM evidence_fts WHERE evidence_fts MATCH 'replacement'").fetchone()[0] == 1
    c.execute("UPDATE evidence_chunks SET searchable=0 WHERE evidence_id='Q'")
    assert c.execute("SELECT count(*) FROM evidence_fts WHERE evidence_fts MATCH 'replacement'").fetchone()[0] == 0
    c.execute("DELETE FROM evidence_chunks WHERE evidence_id='Q'")
    assert c.execute("SELECT count(*) FROM evidence_fts_vocab").fetchone()[0] == 0
    c.close()


def test_field_canonicalization_equivalence_and_difference():
    assert canonicalize_field("range", "150 feet") == canonicalize_field("range", "150 ft.")
    assert canonicalize_field("range", {"value": 150, "units": "ft"}) == "150 ft"
    assert canonicalize_field("range", "120 feet") != canonicalize_field("range", "150 feet")
    assert canonicalize_field("cost", "1 sp") == canonicalize_field("cost", "0.1 gp")
    assert canonicalize_field("cost", {"value": 1, "denomination": "sp"}) == "10 cp"
    assert normalize_evidence("<p>Fireball — text</p>") == normalize_evidence(" Fireball -  text ")
    assert normalize_evidence("does") != normalize_evidence("does not")
    assert normalize_evidence("takes 1d6 damage") != normalize_evidence("takes 1d8 damage")
    assert normalize_evidence("Action (only while prone)") != normalize_evidence("Action")


def test_allowlist_is_explicit_and_does_not_admit_vtt_metadata():
    assert "flags" not in {key for fields in FIELD_ALLOWLIST.values() for key in fields}
    assert "effects" not in {key for fields in FIELD_ALLOWLIST.values() for key in fields}
    assert "img" not in {key for fields in FIELD_ALLOWLIST.values() for key in fields}


def test_diagnostic_selection_uses_kind_before_provider():
    candidates = [
        {"evidence_id": "a", "evidence_kind": "prose", "representation_id": "a", "normalized_digest": "x"},
        {"evidence_id": "b", "evidence_kind": "structured_field", "representation_id": "z", "normalized_digest": "y"},
    ]
    assert rank_evidence(candidates, "field")[0]["evidence_id"] == "b"
    assert rank_evidence(candidates, "explanation")[0]["evidence_id"] == "a"


def test_real_corpus_activation_preserves_alpha62_identity_and_fingerprints():
    c = connect()
    try:
        for representation in ("foundry:srd-5.2", "cantilux:dnd-srd-json"):
            source = c.execute("SELECT id,enabled FROM sources WHERE representation_id=?", (representation,)).fetchone()
            assert source["enabled"] == 1
            assert c.execute("SELECT count(*) FROM evidence_chunks WHERE source_id=? AND searchable=1", (source["id"],)).fetchone()[0] > 0
            assert c.execute("""SELECT count(DISTINCT v.doc) FROM evidence_fts_vocab v
                                JOIN evidence_chunks ec ON ec.id=v.doc WHERE ec.source_id=?""", (source["id"],)).fetchone()[0] > 0
        assert identity_fingerprint(c)["sha256"] == FROZEN_ALPHA61
        assert substantive_corpus_fingerprint(c)["sha256"] == FROZEN_ALPHA51
        first = evidence_fingerprint(c)
        assert first["families"] > 0 and first["facts"] > 0
        assert evidence_fingerprint(c) == first
    finally:
        c.close()


def test_fireball_range_is_equivalent_and_ambiguous_acid_is_isolated():
    c = connect()
    try:
        values = {r[0] for r in c.execute("SELECT canonical_value FROM evidence_facts WHERE family_id=?",
                                          ("wotc:srd-5.2.1/spell/fireball/field/range",))}
        assert values == {"150 ft"}
        assert c.execute("SELECT count(*) FROM evidence_facts WHERE family_id=? AND display_value LIKE '60%'",
                         ("wotc:srd-5.2.1/spell/eyebite/field/range",)).fetchone()[0] == 0
        acid = c.execute("""SELECT count(DISTINCT ef.canonical_entity_id),count(DISTINCT ef.id)
                            FROM evidence_families ef JOIN evidence_family_members m ON m.family_id=ef.id
                            JOIN evidence_chunks ec ON ec.id=m.evidence_chunk_id JOIN content_records cr ON cr.id=ec.content_record_id
                            WHERE lower(cr.name)='acid' AND cr.representation_id='cantilux:dnd-srd-json'""").fetchone()
        assert acid[0] == 0
        assert acid[1] >= 2
        assert c.execute("""SELECT count(*) FROM evidence_chunks ec JOIN content_records cr ON cr.id=ec.content_record_id
                            JOIN evidence_family_members m ON m.evidence_chunk_id=ec.id
                            JOIN evidence_families f ON f.id=m.family_id
                            WHERE lower(cr.name)='acid' AND ec.evidence_kind='table' AND f.family_type='table'""").fetchone()[0] > 0
    finally:
        c.close()


def test_unknown_foundry_helpers_generate_no_evidence_and_duplicates_are_retained():
    c = connect()
    try:
        assert c.execute("""SELECT count(*) FROM evidence_chunks ec JOIN content_records cr ON cr.id=ec.content_record_id
                            JOIN entity_mappings em ON em.content_record_id=cr.id
                            WHERE cr.representation_id='foundry:srd-5.2' AND em.status='unmapped'
                              AND (lower(cr.upstream_path) LIKE '%/monsterfeatures24/%'
                                   OR lower(cr.upstream_path) LIKE '%/equipment24/supplemental/%')""").fetchone()[0] == 0
        assert c.execute("SELECT count(*) FROM evidence_family_members WHERE exact_duplicate_of IS NOT NULL").fetchone()[0] > 0
        assert c.execute("""SELECT count(*) FROM evidence_family_members m
                            LEFT JOIN evidence_chunks ec ON ec.id=m.evidence_chunk_id WHERE ec.id IS NULL""").fetchone()[0] == 0
    finally:
        c.close()


def test_open5e_legacy_chunks_are_not_one_overbroad_entity_summary():
    c = connect()
    try:
        rows = c.execute("""SELECT ef.id,count(*) n FROM evidence_families ef
                            JOIN evidence_family_members m ON m.family_id=ef.id
                            WHERE ef.canonical_entity_id='wotc:srd-5.2.1/class/sorcerer'
                              AND ef.family_type='entity_summary' GROUP BY ef.id""").fetchall()
        assert len(rows) > 10
        assert all(row["n"] == 1 for row in rows)
    finally:
        c.close()


def test_field_equivalence_does_not_claim_whole_record_chunks_are_duplicates():
    c = connect()
    try:
        rows = c.execute("""SELECT m.evidence_role,m.exact_duplicate_of FROM evidence_family_members m
                            JOIN evidence_families f ON f.id=m.family_id WHERE f.family_type='field'""").fetchall()
        assert rows
        assert all(row["evidence_role"] == "observation" and row["exact_duplicate_of"] is None for row in rows)
    finally:
        c.close()


def test_conflict_status_never_votes_three_to_one():
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA)
    c.execute("INSERT INTO evidence_families VALUES('f','a',NULL,'field','range','clear','v')")
    c.execute("INSERT INTO sources(id,name,source_type,authority_type,created_at,updated_at) VALUES('s','s','x','official_srd','n','n')")
    version = c.execute("INSERT INTO source_versions(source_id,content_sha256,imported_at) VALUES('s','x','n')").lastrowid
    for index, value in enumerate(("X", "Y", "Y", "Y")):
        chunk = c.execute("INSERT INTO evidence_chunks(evidence_id,source_id,source_version_id,heading,text) VALUES(?,?,?,?,?)",
                          (f"E{index}", "s", version, "h", value)).lastrowid
        c.execute("INSERT INTO evidence_facts VALUES(?,?,?,?,?,?,?)", (f"fact{index}", "f", chunk, "range", value, value, "v"))
    refresh_conflicts(c)
    assert c.execute("SELECT conflict_status FROM evidence_families WHERE id='f'").fetchone()[0] == "conflicted"
    c.close()


def test_duplicate_primary_and_fingerprint_ignore_member_insertion_order():
    fingerprints = []
    primaries = []
    for order in (("Z", "A", "M"), ("M", "Z", "A")):
        c = sqlite3.connect(":memory:")
        c.row_factory = sqlite3.Row
        c.executescript(SCHEMA)
        c.execute("INSERT INTO sources(id,name,source_type,authority_type,created_at,updated_at) VALUES('s','s','x','official_srd','n','n')")
        version = c.execute("INSERT INTO source_versions(source_id,content_sha256,imported_at) VALUES('s','x','n')").lastrowid
        c.execute("INSERT INTO evidence_families VALUES('f','a',NULL,'prose_rule','description','clear','v')")
        for evidence_id in order:
            chunk = c.execute("INSERT INTO evidence_chunks(evidence_id,source_id,source_version_id,heading,text) VALUES(?,?,?,?,?)",
                              (evidence_id, "s", version, "h", "same text")).lastrowid
            c.execute("INSERT INTO evidence_family_members VALUES(?,?,?,?,?,NULL)",
                      ("f", chunk, evidence_id, "observation", normalized_digest("same text")))
        _finalize_member_roles(c)
        primaries.append(c.execute("""SELECT ec.evidence_id FROM evidence_family_members m JOIN evidence_chunks ec
                                      ON ec.id=m.evidence_chunk_id WHERE m.evidence_role='primary'""").fetchone()[0])
        fingerprints.append(evidence_fingerprint(c)["sha256"])
        c.close()
    assert primaries == ["A", "A"]
    assert fingerprints[0] == fingerprints[1]
