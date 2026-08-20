from __future__ import annotations

import json
import re
import unicodedata
from typing import Any


VALUE_SCHEMA_VERSION = "alpha6.2-v1"

FIELD_ALLOWLIST = {
    "spell": ("level", "school", "casting_time", "range", "components"),
    "monster": ("armor_class", "hit_points", "hit_point_formula", "challenge_rating", "speed"),
    "equipment": ("cost", "weight", "damage", "armor_class"),
    # Magic-item category/rarity vocabularies and feature parent labels are not
    # cleanly equivalent across the alpha.6.1 corpus, so they remain omitted.
    "magic_item": (),
    "class_feature": ("level",),
    "subclass_feature": ("level",),
    "species": ("size", "speed", "creature_type"),
}


def _text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value).strip()
    if isinstance(value, dict):
        if value.get("name") not in (None, ""):
            return str(value["name"]).strip()
        if value.get("value") not in (None, "") and len(value) <= 3:
            units = value.get("units") or value.get("unit") or value.get("denomination") or ""
            return f"{value['value']} {units}".strip()
    if isinstance(value, list) and all(isinstance(x, (str, int, float)) for x in value):
        return ", ".join(map(str, value))
    return None


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().lower()
    value = value.translate(str.maketrans({"’": "'", "–": "-", "—": "-"}))
    return re.sub(r"\s+", " ", value)


def canonicalize_field(field_key: str, value: Any) -> str | None:
    """Narrow field canonicalization; arbitrary prose never enters here."""
    display = _text(value)
    if display is None:
        return None
    plain = _plain(display)
    if field_key == "school":
        return {"abj": "abjuration", "con": "conjuration", "div": "divination", "enc": "enchantment",
                "evo": "evocation", "ill": "illusion", "nec": "necromancy", "trs": "transmutation"}.get(plain, plain)
    if field_key == "casting_time":
        plain = re.sub(r"\s+or ritual$", "", plain)
        plain = plain.replace("bonus-action", "bonus action")
        plain = re.sub(r"^1 action$", "action", plain)
        plain = re.sub(r"^bonus$", "bonus action", plain)
        match = re.match(r"^(action|bonus action|reaction|(?:[0-9]+)\s*(?:minute|hour)s?)", plain)
        if match:
            return re.sub(r"s$", "", re.sub(r"(?<=\d)(?=[a-z])", " ", match.group(1)))
    if field_key == "duration":
        if plain == "inst":
            plain = "instantaneous"
        plain = re.sub(r"^concentration,?\s*(?:up to\s*)?", "concentration ", plain)
        plain = re.sub(r"\s+", " ", plain)
    if field_key in {"range", "speed"}:
        if plain in {"touch", "self", "sight", "unlimited", "special"}:
            return plain
        match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(?:ft\.?|feet|foot)", plain)
        if match:
            return f"{format(float(match.group(1)), 'g')} ft"
        match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(?:mi\.?|miles?)", plain)
        if match:
            return f"{format(float(match.group(1)), 'g')} mi"
        return None
    if field_key == "weight":
        fractions = {"1/4": .25, "1/2": .5, "3/4": .75}
        for token, number in fractions.items():
            if plain.startswith(token + " "):
                plain = plain.replace(token, str(number), 1)
        match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(?:lb\.?|lbs\.?|pounds?)?", plain)
        if match:
            return f"{format(float(match.group(1)), 'g')} lb"
        return None
    if field_key == "cost":
        plain = plain.replace(",", "")
        match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(cp|sp|ep|gp|pp)?", plain)
        if match:
            unit = match.group(2) or "gp"
            copper = float(match.group(1)) * {"cp": 1, "sp": 10, "ep": 50, "gp": 100, "pp": 1000}[unit]
            return f"{format(copper, 'g')} cp"
        return None
    if field_key in {"level", "armor_class", "hit_points", "challenge_rating"}:
        match = re.fullmatch(r"[0-9]+(?:\.0+)?", plain)
        if match:
            return str(int(float(plain)))
    if field_key in {"components", "properties"}:
        if field_key == "components":
            plain = re.sub(r"\s*\(.*\)$", "", plain)
        parts = [re.sub(r"\s+", " ", x.strip()) for x in re.split(r",\s*", plain) if x.strip()]
        return ", ".join(sorted(parts))
    return plain


def _foundry_fields(entity_type: str, data: dict) -> dict[str, Any]:
    system = data.get("system") if isinstance(data.get("system"), dict) else {}
    if entity_type == "spell":
        properties = system.get("properties") or []
        components = [label for key, label in (("vocal", "V"), ("somatic", "S"), ("material", "M")) if key in properties]
        activation = system.get("activation") if isinstance(system.get("activation"), dict) else {}
        casting = f"{activation.get('value') or ''} {activation.get('type') or ''}".strip()
        duration = system.get("duration") if isinstance(system.get("duration"), dict) else {}
        duration_text = f"{duration.get('value') or ''} {duration.get('units') or ''}".strip()
        if "concentration" in properties and duration_text:
            duration_text = "concentration " + duration_text
        return {"level": system.get("level"), "school": system.get("school"),
                "casting_time": casting, "range": system.get("range"),
                "components": components, "duration": duration_text}
    if entity_type == "monster":
        attrs = system.get("attributes") if isinstance(system.get("attributes"), dict) else {}
        details = system.get("details") if isinstance(system.get("details"), dict) else {}
        return {"armor_class": attrs.get("ac"), "hit_points": attrs.get("hp"),
                "hit_point_formula": (attrs.get("hp") or {}).get("formula") if isinstance(attrs.get("hp"), dict) else None,
                "challenge_rating": details.get("cr"), "speed": attrs.get("movement")}
    if entity_type == "equipment":
        price = system.get("price")
        return {"cost": price, "weight": system.get("weight"), "damage": system.get("damage"),
                "properties": system.get("properties"), "armor_class": system.get("armor")}
    if entity_type == "magic_item":
        return {"rarity": system.get("rarity"), "attunement": system.get("attunement") or system.get("attuned"),
                "item_category": system.get("type")}
    if entity_type in {"class_feature", "subclass_feature"}:
        return {"class": data.get("class") or system.get("requirements"), "subclass": data.get("subclass"),
                "level": data.get("level") or system.get("level")}
    if entity_type == "species":
        return {"size": system.get("traits", {}).get("size") if isinstance(system.get("traits"), dict) else None,
                "speed": system.get("movement"), "creature_type": system.get("type")}
    return {}


def _generic_fields(entity_type: str, data: dict) -> dict[str, Any]:
    fields = dict(data)
    if entity_type == "spell":
        fields["range"] = data.get("range_text") or data.get("range")
        if data.get("concentration") and data.get("duration"):
            fields["duration"] = "concentration " + str(data["duration"])
    if entity_type == "monster":
        fields["armor_class"] = data.get("armor_class") or data.get("ac")
        fields["hit_points"] = data.get("hit_points") or data.get("hp")
        fields["challenge_rating"] = data.get("challenge_rating") or data.get("cr")
    if entity_type == "magic_item":
        fields["item_category"] = data.get("item_category") or data.get("category") or data.get("type")
    if entity_type == "species":
        fields["creature_type"] = data.get("creature_type") or data.get("type")
    record = data.get("record") if isinstance(data.get("record"), dict) else {}
    for key in ("cost", "weight", "damage", "properties", "armor_class"):
        if fields.get(key) is None:
            fields[key] = record.get(key)
    return fields


def extract_structured_facts(entity_type: str, representation_id: str, structured_json: str | dict) -> list[dict]:
    data = json.loads(structured_json or "{}") if isinstance(structured_json, str) else structured_json
    if not isinstance(data, dict) or entity_type not in FIELD_ALLOWLIST:
        return []
    raw = _foundry_fields(entity_type, data) if representation_id == "foundry:srd-5.2" else _generic_fields(entity_type, data)
    # Plant Growth has two casting modes; no provider exposes the same scalar
    # scope cleanly enough for a single alpha.6.2 field fact.
    if entity_type == "spell" and str(data.get("name") or "").casefold() == "plant growth":
        raw.pop("casting_time", None)
    # Foundry models Eyebite's 60-foot target selection as system.range even
    # though the SRD casting range is Self. It is not a comparable range fact.
    if (entity_type == "spell" and representation_id == "foundry:srd-5.2"
            and str(data.get("name") or "").casefold() == "eyebite"):
        raw.pop("range", None)
    out = []
    for field_key in FIELD_ALLOWLIST[entity_type]:
        display = _text(raw.get(field_key))
        canonical = canonicalize_field(field_key, raw.get(field_key))
        if display is not None and canonical is not None:
            out.append({"field_key": field_key, "canonical_value": canonical, "display_value": display})
    return out
