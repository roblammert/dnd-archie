from __future__ import annotations

from dataclasses import dataclass
import json


TAXONOMY_VERSION = "alpha6.1-v1"

ENTITY_TYPES = frozenset({
    "spell", "monster", "equipment", "magic_item", "class", "subclass",
    "class_feature", "subclass_feature", "species", "species_trait",
    "background", "feat", "condition", "action", "rule", "glossary",
    "hazard", "area_of_effect", "ability_score", "table", "unknown",
})


@dataclass(frozen=True)
class Classification:
    entity_type: str
    detail: str


OPEN5E_TYPES = {
    "spells": "spell", "creatures": "monster", "backgrounds": "background",
    "classes": "class", "subclasses": "subclass", "feats": "feat",
    "species": "species", "magic_items": "magic_item",
}

CANTILUX_TYPES = {
    "spells": "spell", "monsters": "monster", "backgrounds": "background",
    "classes": "class", "subclasses": "subclass", "feats": "feat",
    "species": "species", "class-features": "class_feature",
    "subclass-features": "subclass_feature", "equipment": "equipment",
    "magic-items": "magic_item", "conditions": "condition", "actions": "action",
    "hazards": "hazard", "areas-of-effect": "area_of_effect",
    "ability-scores": "ability_score", "tables": "table", "rules": "rule",
}


def _data(record) -> dict:
    raw = record["structured_json"] if "structured_json" in record.keys() else None
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def classify(record) -> Classification:
    """Classify one persisted observation without treating importer types as semantic."""
    representation = record["representation_id"] or ""
    content_type = record["content_type"] or ""
    path = (record["upstream_path"] or "").lower()
    data = _data(record)

    if representation == "wotc:official-srd-5.2.1" or content_type == "page":
        return Classification("unknown", "pdf-page-not-an-entity")

    if representation == "open5e:srd-2024":
        entity_type = OPEN5E_TYPES.get(content_type)
        # Open5e equipment is a heterogeneous endpoint; require its explicit category.
        if content_type == "equipment" and (data.get("category") or data.get("equipment_category")):
            entity_type = "equipment"
        return Classification(entity_type or "unknown", f"open5e:{content_type}")

    if representation == "foundry:srd-5.2":
        if "/monsterfeatures24/" in path:
            return Classification("unknown", "foundry-monster-helper")
        if "/equipment24/supplemental/" in path or "/mysterious-deck-cards/" in path:
            return Classification("unknown", "foundry-item-helper")
        if "/equipment24/containers/" in path:
            if path.endswith("/_container.yml"):
                return Classification("magic_item", "foundry-magic-container")
            return Classification("unknown", "foundry-container-helper")
        if content_type == "npc":
            ordinary_actor_packs = (
                "/actors24/aberration/", "/actors24/beast/", "/actors24/celestial/",
                "/actors24/dragon/", "/actors24/elemental/", "/actors24/fey/",
                "/actors24/fiend/", "/actors24/giant/", "/actors24/humanoid/",
                "/actors24/monstrosity/", "/actors24/ooze/", "/actors24/plant/",
                "/actors24/swarm/", "/actors24/undead/",
            )
            if any(pack in path for pack in ordinary_actor_packs):
                return Classification("monster", "foundry-actors24")
            if "/actors24/" in path:
                return Classification("unknown", "foundry-npc-helper")
        direct = {
            "spell": "spell", "background": "background", "class": "class",
            "subclass": "subclass", "race": "species",
        }.get(content_type)
        if direct:
            return Classification(direct, f"foundry-path:{content_type}")
        system = data.get("system") if isinstance(data.get("system"), dict) else {}
        properties = system.get("properties") if isinstance(system.get("properties"), list) else []
        if (content_type in {"weapon", "equipment", "consumable", "loot"}
                and "/equipment24/" in path
                and (system.get("rarity") or "mgc" in properties or "/magical/" in path)):
            return Classification("magic_item", "foundry-equipment24-magical")
        if content_type == "feat":
            if "/classes24/" in path and "/class-features/" in path:
                return Classification("class_feature", "foundry-classfeatures24")
            if "/classes24/" in path and "/subclass-features/" in path:
                return Classification("subclass_feature", "foundry-subclassfeatures24")
            if "/origins24/species/traits/" in path:
                return Classification("species_trait", "foundry-species-trait")
            if "/feats24/" in path:
                return Classification("feat", "foundry-feats24")
        if content_type in {"weapon", "equipment", "tool", "container", "vehicle"} and "/equipment24/" in path:
            return Classification("equipment", "foundry-equipment24")
        if content_type in {"equipment", "consumable", "loot"} and "/magicitems24/" in path:
            return Classification("magic_item", "foundry-magicitems24")
        return Classification("unknown", f"foundry-unclassified:{content_type}")

    if representation == "cantilux:dnd-srd-json":
        collection = data.get("collection")
        if collection != content_type:
            return Classification("unknown", "cantilux-collection-mismatch")
        entity_type = CANTILUX_TYPES.get(collection)
        # Rule definitions are indexes/definitions, not automatically semantic rules.
        if collection == "rule-definitions":
            entity_type = None
        return Classification(entity_type or "unknown", f"cantilux:{collection}")

    return Classification("unknown", "unknown-representation")
