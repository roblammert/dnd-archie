import json

from archie.taxonomy import classify


class Record(dict):
    def keys(self):
        return super().keys()


def record(rep, content_type, path="", data=None):
    return Record(representation_id=rep, content_type=content_type, upstream_path=path,
                  structured_json=json.dumps(data or {}))


def test_open5e_straightforward_types_and_unknown_rules():
    assert classify(record("open5e:srd-2024", "spells")).entity_type == "spell"
    assert classify(record("open5e:srd-2024", "creatures")).entity_type == "monster"
    assert classify(record("open5e:srd-2024", "rules")).entity_type == "unknown"


def test_foundry_importer_types_require_pack_semantics():
    rep = "foundry:srd-5.2"
    assert classify(record(rep, "feat", "packs/_source/monsterfeatures24/actions/x.yml")).entity_type == "unknown"
    assert classify(record(rep, "weapon", "packs/_source/monsterfeatures24/actions/x.yml")).entity_type == "unknown"
    assert classify(record(rep, "npc", "packs/_source/actors24/summons/x.yml")).entity_type == "unknown"
    assert classify(record(rep, "npc", "packs/_source/actors24/construct/x.yml")).entity_type == "unknown"
    assert classify(record(rep, "npc", "packs/_source/actors24/conjurations/arcane-eye.yml")).entity_type == "unknown"
    assert classify(record(rep, "npc", "packs/_source/actors24/magic-items/dancing-sword.yml")).entity_type == "unknown"
    assert classify(record(rep, "npc", "packs/_source/actors24/companions/otherworldly-steed.yml")).entity_type == "unknown"
    assert classify(record(rep, "npc", "packs/_source/actors24/dragon/x.yml")).entity_type == "monster"
    assert classify(record(rep, "equipment", "packs/_source/equipment24/armor/magical/x.yml",
                           {"system": {"rarity": "rare", "properties": ["mgc"]}})).entity_type == "magic_item"
    assert classify(record(rep, "weapon", "packs/_source/equipment24/weapons/x.yml",
                           {"system": {"rarity": "", "properties": []}})).entity_type == "equipment"
    assert classify(record(rep, "container", "packs/_source/equipment24/containers/bag-of-holding/_container.yml")).entity_type == "magic_item"
    assert classify(record(rep, "equipment", "packs/_source/equipment24/containers/folding-boat/activate.yml")).entity_type == "unknown"
    assert classify(record(rep, "consumable", "packs/_source/equipment24/equipment/mysterious-deck-cards/sun.yml",
                           {"system": {"properties": ["mgc"]}})).entity_type == "unknown"


def test_cantilux_collection_identity_controls_classification():
    rep = "cantilux:dnd-srd-json"
    assert classify(record(rep, "tables", data={"collection": "tables"})).entity_type == "table"
    assert classify(record(rep, "class-features", data={"collection": "class-features"})).entity_type == "class_feature"
    assert classify(record(rep, "rule-definitions", data={"collection": "rule-definitions"})).entity_type == "unknown"
    assert classify(record(rep, "spells", data={"collection": "tables"})).entity_type == "unknown"


def test_pdf_pages_are_not_entities():
    assert classify(record("wotc:official-srd-5.2.1", "page")).entity_type == "unknown"
