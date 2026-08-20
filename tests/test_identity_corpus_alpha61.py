from archie.config import settings
from archie.db import connect
from archie.identity import identity_fingerprint
from archie.source_library import substantive_corpus_fingerprint


FROZEN_ALPHA51 = "1ee9f26b61a32f74dade72116dff397109c49f859f2bd04386553128f9b7b27f"


def test_real_corpus_identity_and_frozen_substantive_fingerprint():
    assert settings.database.exists(), "run ingest before corpus acceptance tests"
    c = connect()
    try:
        assert substantive_corpus_fingerprint(c)["sha256"] == FROZEN_ALPHA51
        fingerprint = identity_fingerprint(c)
        assert fingerprint["canonical_entities"] > 0
        assert fingerprint["mappings"] > 0
        assert len(fingerprint["sha256"]) == 64
        assert c.execute("""SELECT count(*) FROM entity_mappings em JOIN content_records cr ON cr.id=em.content_record_id
                            WHERE cr.content_type='page'""").fetchone()[0] == 0
    finally:
        c.close()


def test_foundry_and_cantilux_activation_preserves_identity_corpus():
    c = connect()
    try:
        for representation in ("foundry:srd-5.2", "cantilux:dnd-srd-json"):
            source = c.execute("SELECT id,enabled FROM sources WHERE representation_id=?", (representation,)).fetchone()
            assert source["enabled"] == 1
            assert c.execute("SELECT count(*) FROM evidence_chunks WHERE source_id=? AND searchable=1", (source["id"],)).fetchone()[0] > 0
            assert c.execute("""SELECT count(DISTINCT v.doc) FROM evidence_fts_vocab v JOIN evidence_chunks e ON e.id=v.doc
                                WHERE e.source_id=?""", (source["id"],)).fetchone()[0] > 0
    finally:
        c.close()


def test_no_foundry_monster_helper_leaks_to_feat_or_equipment():
    c = connect()
    try:
        leaked = c.execute("""SELECT count(*) FROM entity_mappings em
            JOIN content_records cr ON cr.id=em.content_record_id
            JOIN canonical_entities ce ON ce.id=em.canonical_entity_id
            WHERE cr.representation_id='foundry:srd-5.2'
              AND lower(cr.upstream_path) LIKE '%/monsterfeatures24/%'
              AND ce.entity_type IN ('feat','equipment')""").fetchone()[0]
        assert leaked == 0
    finally:
        c.close()


def test_no_canonical_entity_hides_same_representation_duplicates():
    c = connect()
    try:
        duplicates = c.execute("""SELECT em.canonical_entity_id,cr.representation_id,count(*) n
            FROM entity_mappings em JOIN content_records cr ON cr.id=em.content_record_id
            WHERE em.status='mapped' GROUP BY em.canonical_entity_id,cr.representation_id
            HAVING count(*)>1""").fetchall()
        assert duplicates == []
    finally:
        c.close()


def test_foundry_actor_and_item_helpers_are_unknown_and_unmapped():
    c = connect()
    try:
        helper_patterns = ("%/actors24/conjurations/%", "%/actors24/magic-items/%",
                           "%/actors24/companions/%", "%/mysterious-deck-cards/%",
                           "%/equipment24/supplemental/%")
        for pattern in helper_patterns:
            rows = c.execute("""SELECT em.status,em.canonical_entity_id FROM entity_mappings em
                JOIN content_records cr ON cr.id=em.content_record_id
                WHERE cr.representation_id='foundry:srd-5.2' AND lower(cr.upstream_path) LIKE ?""",
                (pattern,)).fetchall()
            assert rows
            assert all(r["status"] == "unmapped" and r["canonical_entity_id"] is None for r in rows)
    finally:
        c.close()


def test_parent_links_have_only_locked_type_pairs_and_no_cycles():
    c = connect()
    try:
        pairs = {(r["child"], r["parent"]) for r in c.execute("""SELECT ch.entity_type child,p.entity_type parent
            FROM canonical_entities ch JOIN canonical_entities p ON p.id=ch.parent_entity_id""")}
        assert pairs <= {("class_feature", "class"), ("subclass_feature", "subclass"),
                         ("species_trait", "species")}
        assert c.execute("""SELECT count(*) FROM canonical_entities ch JOIN canonical_entities p
            ON p.id=ch.parent_entity_id WHERE ch.authority_id<>p.authority_id""").fetchone()[0] == 0
        cycles = c.execute("""WITH RECURSIVE walk(origin,id,parent,depth) AS (
              SELECT id,id,parent_entity_id,0 FROM canonical_entities
              UNION ALL SELECT walk.origin,p.id,p.parent_entity_id,depth+1 FROM walk
              JOIN canonical_entities p ON p.id=walk.parent WHERE depth<100)
            SELECT count(*) FROM walk WHERE origin=parent""").fetchone()[0]
        assert cycles == 0
    finally:
        c.close()
