from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import re
import unicodedata

from .taxonomy import TAXONOMY_VERSION, classify


AUTHORITY_ID = "wotc:srd-5.2.1"
MAPPING_VERSION = "alpha6.1-v1"
MAPPING_STATUSES = frozenset({"mapped", "unmapped", "ambiguous"})
MAPPING_METHODS = frozenset({"structural_id", "explicit_crosswalk", "semantic_key", "reviewed_alias", "singleton", "none"})


def normalize_key(value: str) -> str:
    """Narrow, versioned normalization; meaningful words and numbers survive."""
    value = unicodedata.normalize("NFKC", value or "").lower()
    value = value.translate(str.maketrans({"’": "'", "‘": "'", "`": "'", "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "―": "-"}))
    value = re.sub(r"[^\w'/-]+", "-", value, flags=re.UNICODE)
    value = re.sub(r"[-/]+", lambda m: "/" if "/" in m.group(0) else "-", value)
    return value.strip("-/")


def canonical_entity_id(entity_type: str, canonical_key: str) -> str:
    return f"{AUTHORITY_ID}/{entity_type.replace('_', '-')}/{canonical_key}"


def select_mapping_method(*, structural_id=False, explicit_crosswalk=False, semantic_key=False, reviewed_alias=False, singleton=False) -> str:
    for enabled, method in ((structural_id, "structural_id"), (explicit_crosswalk, "explicit_crosswalk"),
                            (semantic_key, "semantic_key"), (reviewed_alias, "reviewed_alias"),
                            (singleton, "singleton")):
        if enabled:
            return method
    return "none"


@dataclass(frozen=True)
class Observation:
    record_id: int
    representation_id: str
    entity_type: str
    key: str | None
    name: str
    parent_key: str | None = None


def _json(record) -> dict:
    try:
        value = json.loads(record["structured_json"] or "{}")
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def _feature_context(record, entity_type: str, data: dict) -> tuple[str, str, str] | None:
    system = data.get("system") if isinstance(data.get("system"), dict) else {}
    prerequisites = system.get("prerequisites") if isinstance(system.get("prerequisites"), dict) else {}
    source = data.get("source") if isinstance(data.get("source"), dict) else {}
    parent = data.get("class") or data.get("className") or data.get("parentClass")
    subclass = data.get("subclass") or data.get("subclassName") or data.get("parentSubclass")
    parent = parent.get("name") if isinstance(parent, dict) else parent
    subclass = subclass.get("name") if isinstance(subclass, dict) else subclass
    requirement = system.get("requirements")
    if entity_type == "class_feature" and not parent:
        parent = requirement
    if entity_type == "subclass_feature" and not subclass:
        subclass = requirement
    level = data.get("level") or data.get("gainedAt") or data.get("gained_at") or prerequisites.get("level")
    path_parts = source.get("path") if isinstance(source.get("path"), list) else []
    text = " / ".join(str(x) for x in path_parts)
    foundry_class = re.search(r"/classes24/([^/]+)/", (record["upstream_path"] or "").lower())
    if not parent and foundry_class:
        parent = foundry_class.group(1)
    match = re.search(r"\b(Barbarian|Bard|Cleric|Druid|Fighter|Monk|Paladin|Ranger|Rogue|Sorcerer|Warlock|Wizard)\b", text, re.I)
    path_parent = match.group(1) if match else None
    if parent and path_parent and normalize_key(str(parent)) != normalize_key(path_parent):
        return None
    if not parent:
        parent = path_parent
    subclass_match = re.search(r"Subclass:\s*([^/]+?)(?:\s*/|$)", text, re.I)
    path_subclass = subclass_match.group(1).strip() if subclass_match else None
    if subclass and path_subclass and normalize_key(str(subclass)) != normalize_key(path_subclass):
        return None
    if not subclass:
        subclass = path_subclass
    if entity_type == "subclass_feature" and not subclass and len(path_parts) >= 2:
        subclass = path_parts[-2]
    if not level:
        match = re.search(r"(?:level|lvl)[ -]?(\d+)", text, re.I)
        level = match.group(1) if match else None
    if isinstance(level, list):
        level = level[0].get("level") if len(level) == 1 and isinstance(level[0], dict) else None
    parent_value = subclass if entity_type == "subclass_feature" else parent
    if entity_type == "subclass_feature":
        if not parent or not subclass:
            return None
        parent_value = f"{normalize_key(str(parent))}/{normalize_key(str(subclass))}"
    if not parent_value or level in (None, "") or not record["name"]:
        return None
    feature_name = re.sub(rf"^level\s+{re.escape(str(level))}\s*:\s*", "", record["name"], flags=re.I)
    return normalize_key(str(parent_value)), normalize_key(str(level)), normalize_key(feature_name)


def observation_from_record(record) -> Observation:
    classification = classify(record)
    name = record["name"] or ""
    if classification.entity_type == "unknown" or not name.strip():
        return Observation(record["id"], record["representation_id"], classification.entity_type, None, name)
    data = _json(record)
    if classification.entity_type in {"class_feature", "subclass_feature"}:
        context = _feature_context(record, classification.entity_type, data)
        if not context:
            return Observation(record["id"], record["representation_id"], classification.entity_type, None, name)
        parent, level, feature = context
        parent_key = parent.split("/", 1)[-1] if classification.entity_type == "subclass_feature" else parent
        return Observation(record["id"], record["representation_id"], classification.entity_type,
                           f"{parent}/{level}/{feature}", name, parent_key)
    if classification.entity_type == "species_trait":
        system = data.get("system") if isinstance(data.get("system"), dict) else {}
        parent = system.get("requirements")
        if not parent:
            return Observation(record["id"], record["representation_id"], classification.entity_type, None, name)
        parent_key = normalize_key(str(parent))
        return Observation(record["id"], record["representation_id"], classification.entity_type,
                           f"{parent_key}/{normalize_key(name)}", name, parent_key)
    return Observation(record["id"], record["representation_id"], classification.entity_type, normalize_key(name), name)


def build_identity(c) -> dict:
    """Rebuild deterministic identity state after all representations are normalized."""
    c.execute("DELETE FROM entity_mappings")
    c.execute("DELETE FROM canonical_entities")
    records = c.execute("""SELECT id,representation_id,content_type,name,upstream_id,upstream_path,structured_json
                           FROM content_records WHERE content_type <> 'page' ORDER BY representation_id,upstream_path,upstream_id,id""").fetchall()
    observations = [observation_from_record(row) for row in records]
    usable = defaultdict(list)
    for obs in observations:
        if obs.key:
            usable[(obs.entity_type, obs.key)].append(obs)

    collision_count = 0
    entities = {}
    mappings = []
    for group_key in sorted(usable):
        entity_type, key = group_key
        group = usable[group_key]
        per_rep = Counter(o.representation_id for o in group)
        if any(n > 1 for n in per_rep.values()):
            collision_count += 1
            candidates = [canonical_entity_id(entity_type, key)]
            detail = json.dumps({"candidates": candidates, "reason": "same-representation-key-collision"}, sort_keys=True, separators=(",", ":"))
            mappings.extend((o, None, "ambiguous", "none", detail) for o in group)
            continue
        entity_id = canonical_entity_id(entity_type, key)
        display_name = sorted((o.name for o in group), key=lambda x: (x.casefold(), x))[0]
        entities[entity_id] = (entity_id, AUTHORITY_ID, entity_type, key, display_name, None, TAXONOMY_VERSION, "identity-builder")
        method = "semantic_key" if len(group) > 1 else "singleton"
        mappings.extend((o, entity_id, "mapped", method, None) for o in group)

    parent_types = {"class_feature": "class", "subclass_feature": "subclass", "species_trait": "species"}
    for entity_id, entity in list(entities.items()):
        entity_type, key = entity[2], entity[3]
        parent_type = parent_types.get(entity_type)
        if not parent_type or "/" not in key:
            continue
        parts = key.split("/")
        parent_key = parts[1] if entity_type == "subclass_feature" and len(parts) > 1 else parts[0]
        parent_id = canonical_entity_id(parent_type, parent_key)
        if parent_id in entities:
            entities[entity_id] = entity[:5] + (parent_id,) + entity[6:]

    mapped_ids = {o.record_id for o, *_ in mappings}
    for obs in observations:
        if obs.record_id not in mapped_ids:
            detail = json.dumps({"reason": "unknown-classification" if obs.entity_type == "unknown" else "insufficient-structural-context"}, sort_keys=True, separators=(",", ":"))
            mappings.append((obs, None, "unmapped", "none", detail))

    entity_rows = sorted(entities.values(), key=lambda row: (row[5] is not None, row[0]))
    c.executemany("""INSERT INTO canonical_entities(id,authority_id,entity_type,canonical_key,display_name,parent_entity_id,taxonomy_version,created_by)
                     VALUES(?,?,?,?,?,?,?,?)""", entity_rows)
    c.executemany("""INSERT INTO entity_mappings(content_record_id,canonical_entity_id,status,method,mapping_key,mapping_version,detail_json)
                     VALUES(?,?,?,?,?,?,?)""",
                  [(o.record_id, entity_id, status, method, o.key, MAPPING_VERSION, detail)
                   for o, entity_id, status, method, detail in sorted(mappings, key=lambda x: x[0].record_id)])
    return identity_report(c) | {"collisions": collision_count}


def identity_fingerprint(c) -> dict:
    entities = [dict(r) for r in c.execute("""SELECT id,authority_id,entity_type,canonical_key,display_name,parent_entity_id,taxonomy_version,created_by
                                               FROM canonical_entities ORDER BY id""")]
    mappings = [dict(r) for r in c.execute("""SELECT cr.representation_id,cr.upstream_id,cr.upstream_path,em.canonical_entity_id,
                                                      em.status,em.method,em.mapping_key,em.mapping_version,em.detail_json
                                               FROM entity_mappings em JOIN content_records cr ON cr.id=em.content_record_id
                                               ORDER BY cr.representation_id,cr.upstream_path,cr.upstream_id,em.mapping_key""")]
    payload = {"taxonomy_version": TAXONOMY_VERSION, "entities": entities, "mappings": mappings}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "canonical_entities": len(entities), "mappings": len(mappings)}


def identity_report(c) -> dict:
    rows = c.execute("""SELECT cr.id,cr.representation_id,cr.content_type,cr.name,cr.upstream_id,cr.upstream_path,cr.structured_json,
                               em.status,em.method
                        FROM entity_mappings em JOIN content_records cr ON cr.id=em.content_record_id""").fetchall()
    classified = [(row, classify(row).entity_type) for row in rows]
    summary = {
        "considered": len(rows),
        "classified": sum(entity_type != "unknown" for _, entity_type in classified),
        "unknown": sum(entity_type == "unknown" for _, entity_type in classified),
        "mapped": sum(row["status"] == "mapped" for row, _ in classified),
        "singleton": sum(row["method"] == "singleton" for row, _ in classified),
        "unmapped": sum(row["status"] == "unmapped" for row, _ in classified),
        "ambiguous": sum(row["status"] == "ambiguous" for row, _ in classified),
    }
    summary["canonical_entities"] = c.execute("SELECT count(*) FROM canonical_entities").fetchone()[0]
    groups = defaultdict(lambda: Counter(records=0, mapped=0, singleton=0, unmapped=0, ambiguous=0))
    for row, entity_type in classified:
        values = groups[(row["representation_id"], entity_type)]
        values["records"] += 1
        values[row["status"]] += 1
        values["singleton"] += row["method"] == "singleton"
    summary["by_representation_type"] = [
        {"representation_id": rep, "entity_type": entity_type, **dict(groups[(rep, entity_type)])}
        for rep, entity_type in sorted(groups)
    ]
    return summary
