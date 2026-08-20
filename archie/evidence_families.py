from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import html
import json
import re
import unicodedata

from .identity import AUTHORITY_ID
from .structured_facts import VALUE_SCHEMA_VERSION, extract_structured_facts
from .evidence_selection import SELECTION_VERSION
from .taxonomy import classify


FAMILY_TYPES = frozenset({"entity_summary", "prose_rule", "field", "table", "feature"})
EVIDENCE_KINDS = frozenset({"pdf_prose", "prose", "structured_record", "structured_field", "table"})
ACTIVATABLE_REPRESENTATIONS = frozenset({"foundry:srd-5.2", "cantilux:dnd-srd-json"})


def set_representation_searchable(c, source_id: str, enabled: bool) -> int:
    """Atomically toggle eligible family evidence without rebuilding or changing IDs."""
    c.execute("UPDATE evidence_chunks SET searchable=0 WHERE source_id=?", (source_id,))
    if enabled:
        c.execute('''UPDATE evidence_chunks SET searchable=1
                     WHERE source_id=? AND EXISTS (
                       SELECT 1 FROM evidence_family_members m
                       JOIN evidence_families f ON f.id=m.family_id
                       LEFT JOIN entity_mappings em ON em.content_record_id=evidence_chunks.content_record_id
                       WHERE m.evidence_chunk_id=evidence_chunks.id
                         AND coalesce(em.status,'unmapped')<>'ambiguous'
                     )''', (source_id,))
    return c.execute("SELECT count(*) FROM evidence_chunks WHERE source_id=? AND searchable=1", (source_id,)).fetchone()[0]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-") or "record"


def family_id(authority_id: str, entity_scope: str, family_type: str, semantic_key: str) -> str:
    if family_type not in FAMILY_TYPES:
        raise ValueError(f"Unsupported family type: {family_type}")
    return f"{authority_id}/{entity_scope}/{family_type}/{_slug(semantic_key)}"


def normalize_evidence(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = unicodedata.normalize("NFKC", value)
    value = value.translate(str.maketrans({"’": "'", "‘": "'", "–": "-", "—": "-"}))
    value = re.sub(r"[*_`#]+", "", value)
    return re.sub(r"\s+", " ", value).strip().casefold()


def normalized_digest(value: str) -> str:
    return hashlib.sha256(normalize_evidence(value).encode()).hexdigest()


def _data(row) -> dict:
    try:
        value = json.loads(row["structured_json"] or "{}")
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def _description(representation: str, data: dict) -> str | None:
    if representation == "foundry:srd-5.2":
        system = data.get("system") if isinstance(data.get("system"), dict) else {}
        desc = system.get("description")
        value = desc.get("value") if isinstance(desc, dict) else desc
    else:
        value = data.get("desc") or data.get("text") or data.get("content")
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"<br\s*/?>", "\n", html.unescape(value), flags=re.I)
    cleaned = re.sub(r"</p\s*>", "\n", cleaned, flags=re.I)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = re.sub(r"\[\[/r\s+([^\]]+)\]\]", r"\1", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned or None


def _safe_unmapped(row, entity_type: str) -> bool:
    if row["status"] == "ambiguous":
        return entity_type != "unknown"
    if entity_type != "unknown":
        return True
    # Cantilux rule prose is an explicit player-facing resource, not a VTT helper.
    return (row["representation_id"] == "cantilux:dnd-srd-json"
            and row["content_type"] in {"rules", "rule-definitions", "glossary"})


def _scope(row, entity_type: str) -> tuple[str, str | None] | None:
    if row["status"] == "mapped":
        return row["canonical_entity_id"].removeprefix(AUTHORITY_ID + "/"), row["canonical_entity_id"]
    if not _safe_unmapped(row, entity_type):
        return None
    stable = row["upstream_id"] or row["upstream_path"] or str(row["content_record_id"])
    digest = hashlib.sha1(stable.encode()).hexdigest()[:12]
    return f"isolated/{_slug(row['representation_id'])}/{_slug(stable)[:60]}-{digest}", None


def _eid(row, kind: str, key: str) -> str:
    stable = f"{row['representation_id']}|{row['upstream_id']}|{row['upstream_path']}|{kind}|{key}"
    prefix = "FND" if row["representation_id"].startswith("foundry") else "CAN"
    return f"{prefix}-{_slug(row['name'])[:36].upper()}-{hashlib.sha1(stable.encode()).hexdigest()[:12].upper()}"


def _insert_family(c, fid: str, canonical_entity_id: str | None, family_type: str, semantic_key: str) -> None:
    c.execute("""INSERT OR IGNORE INTO evidence_families
                 (id,authority_id,canonical_entity_id,family_type,semantic_key,conflict_status,selection_version)
                 VALUES(?,?,?,?,?,'clear',?)""",
              (fid, AUTHORITY_ID, canonical_entity_id, family_type, semantic_key, SELECTION_VERSION))


def _insert_member(c, fid: str, chunk_id: int, representation: str, text: str) -> None:
    digest = normalized_digest(text)
    c.execute("""INSERT INTO evidence_family_members
                 (family_id,evidence_chunk_id,representation_id,evidence_role,normalized_digest,exact_duplicate_of)
                 VALUES(?,?,?,?,?,NULL)""", (fid, chunk_id, representation, "observation", digest))


def _finalize_member_roles(c) -> None:
    """Choose duplicate primaries by stable evidence ID, never insertion/row order.

    Field members compare scoped canonical facts but often point at a record
    containing other fields. They therefore remain observations rather than
    claiming that the complete chunks are exact duplicates.
    """
    c.execute("UPDATE evidence_family_members SET evidence_role='observation',exact_duplicate_of=NULL")
    groups = c.execute("""SELECT m.family_id,m.normalized_digest
                          FROM evidence_family_members m JOIN evidence_families f ON f.id=m.family_id
                          WHERE f.family_type<>'field'
                          GROUP BY m.family_id,m.normalized_digest""").fetchall()
    for family, digest in groups:
        members = c.execute("""SELECT m.evidence_chunk_id FROM evidence_family_members m
                               JOIN evidence_chunks ec ON ec.id=m.evidence_chunk_id
                               WHERE m.family_id=? AND m.normalized_digest=? ORDER BY ec.evidence_id""",
                            (family, digest)).fetchall()
        primary = members[0][0]
        c.execute("UPDATE evidence_family_members SET evidence_role='primary' WHERE family_id=? AND evidence_chunk_id=?",
                  (family, primary))
        for member in members[1:]:
            c.execute("""UPDATE evidence_family_members SET evidence_role='equivalent',exact_duplicate_of=?
                         WHERE family_id=? AND evidence_chunk_id=?""", (primary, family, member[0]))


def refresh_conflicts(c) -> None:
    """Conflict is distinct substantive values, never representation votes."""
    c.execute("UPDATE evidence_families SET conflict_status='clear'")
    c.execute("""UPDATE evidence_families SET conflict_status='conflicted'
                 WHERE family_type='field' AND id IN (
                   SELECT family_id FROM evidence_facts GROUP BY family_id HAVING count(DISTINCT canonical_value)>1
                 )""")


def _insert_chunk(c, row, evidence_id: str, heading: str, text: str, kind: str) -> int:
    cur = c.execute("""INSERT INTO evidence_chunks
        (evidence_id,source_id,source_version_id,content_record_id,page_pdf,page_label,heading,text,evidence_kind,searchable)
        VALUES(?,?,?,?,NULL,NULL,?,?,?,0)""",
        (evidence_id, row["source_id"], row["source_version_id"], row["content_record_id"], heading, text, kind))
    return cur.lastrowid


def _attach_existing_open5e(c) -> int:
    total = 0
    rows = c.execute("""SELECT ec.id,ec.text,cr.id content_record_id,cr.representation_id,cr.content_type,cr.name,
                               cr.upstream_id,cr.upstream_path,cr.structured_json,em.status,em.canonical_entity_id
                        FROM evidence_chunks ec JOIN content_records cr ON cr.id=ec.content_record_id
                        LEFT JOIN entity_mappings em ON em.content_record_id=cr.id
                        WHERE cr.representation_id='open5e:srd-2024' ORDER BY ec.evidence_id""").fetchall()
    first_by_record = {}
    for row in rows:
        entity_type = classify(row).entity_type
        scope = _scope(row, entity_type)
        if not scope:
            continue
        entity_scope, canonical_entity_id = scope
        family_type = "feature" if entity_type.endswith("feature") else "entity_summary"
        semantic_key = c.execute("SELECT evidence_id FROM evidence_chunks WHERE id=?", (row["id"],)).fetchone()[0]
        fid = family_id(AUTHORITY_ID, entity_scope, family_type, semantic_key)
        _insert_family(c, fid, canonical_entity_id, family_type, semantic_key)
        _insert_member(c, fid, row["id"], row["representation_id"], row["text"])
        first_by_record.setdefault(row["content_record_id"], row)
        total += 1
    for row in first_by_record.values():
        entity_type = classify(row).entity_type
        scope = _scope(row, entity_type)
        for fact in extract_structured_facts(entity_type, row["representation_id"], row["structured_json"]):
            fid = family_id(AUTHORITY_ID, scope[0], "field", fact["field_key"])
            _insert_family(c, fid, scope[1], "field", fact["field_key"])
            _insert_member(c, fid, row["id"], row["representation_id"], f"{fact['field_key']}: {fact['canonical_value']}")
            fact_id = hashlib.sha256(f"{fid}|{row['id']}|{fact['field_key']}".encode()).hexdigest()
            c.execute("""INSERT INTO evidence_facts(id,family_id,evidence_chunk_id,field_key,canonical_value,display_value,value_schema_version)
                         VALUES(?,?,?,?,?,?,?)""", (fact_id, fid, row["id"], fact["field_key"], fact["canonical_value"], fact["display_value"], VALUE_SCHEMA_VERSION))
    return total


def build_evidence_families(c) -> dict:
    """Build additive diagnostic evidence after alpha.6.1 identity is complete."""
    c.execute("DELETE FROM evidence_facts")
    c.execute("DELETE FROM evidence_family_members")
    c.execute("DELETE FROM evidence_families")
    c.execute("DELETE FROM evidence_chunks WHERE searchable=0")
    c.execute("UPDATE evidence_chunks SET evidence_kind='pdf_prose',searchable=1 WHERE page_pdf IS NOT NULL")
    c.execute("UPDATE evidence_chunks SET evidence_kind='structured_record',searchable=1 WHERE source_id='open5e:srd-2024'")
    attached = _attach_existing_open5e(c)

    records = c.execute("""SELECT cr.id content_record_id,cr.source_id,cr.source_version_id,cr.external_id,cr.content_type,
                                  cr.name,cr.representation_id,cr.upstream_id,cr.upstream_path,cr.structured_json,
                                  em.status,em.canonical_entity_id
                           FROM content_records cr JOIN entity_mappings em ON em.content_record_id=cr.id
                           WHERE cr.representation_id IN ('foundry:srd-5.2','cantilux:dnd-srd-json')
                           ORDER BY cr.representation_id,cr.upstream_path,cr.upstream_id,cr.id""").fetchall()
    created = 0
    for row in records:
        entity_type = classify(row).entity_type
        scope = _scope(row, entity_type)
        if not scope:
            continue
        entity_scope, canonical_entity_id = scope
        data = _data(row)
        description = _description(row["representation_id"], data)
        if description:
            ftype = "feature" if entity_type.endswith("feature") else "prose_rule"
            fid = family_id(AUTHORITY_ID, entity_scope, ftype, "description")
            _insert_family(c, fid, canonical_entity_id, ftype, "description")
            chunk_id = _insert_chunk(c, row, _eid(row, "prose", "description"), row["name"] or entity_type, description, "prose")
            _insert_member(c, fid, chunk_id, row["representation_id"], description)
            created += 1
        facts = extract_structured_facts(entity_type, row["representation_id"], row["structured_json"])
        fact_chunk_id = None
        if facts:
            table_record = data.get("record") if isinstance(data.get("record"), dict) else None
            fact_text = (json.dumps(table_record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                         if table_record else
                         "\n".join(f"{f['field_key'].replace('_', ' ').title()}: {f['display_value']}" for f in facts))
            fact_kind = "table" if table_record else "structured_record"
            fact_chunk_id = _insert_chunk(c, row, _eid(row, fact_kind, "fields"), row["name"] or entity_type, fact_text, fact_kind)
            if table_record:
                table_fid = family_id(AUTHORITY_ID, entity_scope, "table", "record")
                _insert_family(c, table_fid, canonical_entity_id, "table", "record")
                _insert_member(c, table_fid, fact_chunk_id, row["representation_id"], fact_text)
            created += 1
        for fact in facts:
            fid = family_id(AUTHORITY_ID, entity_scope, "field", fact["field_key"])
            _insert_family(c, fid, canonical_entity_id, "field", fact["field_key"])
            chunk_id = fact_chunk_id
            _insert_member(c, fid, chunk_id, row["representation_id"], f"{fact['field_key']}: {fact['canonical_value']}")
            fact_id = hashlib.sha256(f"{fid}|{row['representation_id']}|{row['upstream_id']}|{fact['field_key']}".encode()).hexdigest()
            c.execute("""INSERT INTO evidence_facts(id,family_id,evidence_chunk_id,field_key,canonical_value,display_value,value_schema_version)
                         VALUES(?,?,?,?,?,?,?)""", (fact_id, fid, chunk_id, fact["field_key"], fact["canonical_value"], fact["display_value"], VALUE_SCHEMA_VERSION))
        tables = data.get("tables") if isinstance(data.get("tables"), list) else []
        for index, table in enumerate(tables):
            if not table:
                continue
            text = json.dumps(table, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            fid = family_id(AUTHORITY_ID, entity_scope, "table", f"table-{index + 1}")
            _insert_family(c, fid, canonical_entity_id, "table", f"table-{index + 1}")
            chunk_id = _insert_chunk(c, row, _eid(row, "table", str(index)), row["name"] or "Table", text, "table")
            _insert_member(c, fid, chunk_id, row["representation_id"], text)
            created += 1

    refresh_conflicts(c)
    _finalize_member_roles(c)
    # Alpha.6.3 ambiguity policy is representation-independent: ambiguous
    # observations never enter ordinary retrieval, including legacy Open5e rows.
    c.execute('''UPDATE evidence_chunks SET searchable=0
                 WHERE content_record_id IN (
                   SELECT content_record_id FROM entity_mappings WHERE status='ambiguous'
                 )''')
    for source_id in sorted(ACTIVATABLE_REPRESENTATIONS):
        enabled = c.execute("SELECT enabled FROM sources WHERE id=?", (source_id,)).fetchone()
        if enabled:
            set_representation_searchable(c, source_id, bool(enabled[0]))
    return evidence_report(c) | {"created_quarantined": created, "attached_existing": attached}


def evidence_fingerprint(c) -> dict:
    chunks = [dict(r) for r in c.execute("""SELECT ec.evidence_id,cr.representation_id,cr.upstream_id,cr.upstream_path,
                                                    ec.heading,ec.text,ec.evidence_kind,
                                                    CASE
                                                      WHEN cr.representation_id IN ('foundry:srd-5.2','cantilux:dnd-srd-json') THEN 0
                                                      WHEN cr.representation_id='open5e:srd-2024' AND em.status='ambiguous' THEN 1
                                                      ELSE ec.searchable END searchable
                                             FROM evidence_chunks ec LEFT JOIN content_records cr ON cr.id=ec.content_record_id
                                             LEFT JOIN entity_mappings em ON em.content_record_id=cr.id
                                             ORDER BY ec.evidence_id""")]
    families = [dict(r) for r in c.execute("SELECT * FROM evidence_families ORDER BY id")]
    members = [dict(r) for r in c.execute("""SELECT efm.family_id,ec.evidence_id,efm.representation_id,efm.evidence_role,
                                                    efm.normalized_digest,dup.evidence_id exact_duplicate_of
                                             FROM evidence_family_members efm JOIN evidence_chunks ec ON ec.id=efm.evidence_chunk_id
                                             LEFT JOIN evidence_chunks dup ON dup.id=efm.exact_duplicate_of
                                             ORDER BY efm.family_id,ec.evidence_id""")]
    facts = [dict(r) for r in c.execute("""SELECT ef.id,ef.family_id,ec.evidence_id,ef.field_key,ef.canonical_value,
                                                  ef.display_value,ef.value_schema_version
                                           FROM evidence_facts ef JOIN evidence_chunks ec ON ec.id=ef.evidence_chunk_id
                                           ORDER BY ef.id""")]
    payload = {"schema_version": VALUE_SCHEMA_VERSION, "chunks": chunks, "families": families, "members": members, "facts": facts}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    return {"sha256": digest, "evidence_chunks": len(chunks), "families": len(families), "facts": len(facts)}


def evidence_report(c) -> dict:
    by_rep = [dict(r) for r in c.execute("""SELECT coalesce(cr.representation_id,s.representation_id) representation_id,
                                                   count(*) evidence_count,sum(ec.searchable) searchable,
                                                   sum(CASE WHEN ec.searchable=0 THEN 1 ELSE 0 END) quarantined
                                            FROM evidence_chunks ec JOIN sources s ON s.id=ec.source_id
                                            LEFT JOIN content_records cr ON cr.id=ec.content_record_id
                                            GROUP BY coalesce(cr.representation_id,s.representation_id) ORDER BY representation_id""")]
    kinds = {r["evidence_kind"]: r["n"] for r in c.execute("SELECT evidence_kind,count(*) n FROM evidence_chunks GROUP BY evidence_kind")}
    types = {r["family_type"]: r["n"] for r in c.execute("SELECT family_type,count(*) n FROM evidence_families GROUP BY family_type")}
    fact_fields = {r["field_key"]: r["n"] for r in c.execute("SELECT field_key,count(*) n FROM evidence_facts GROUP BY field_key")}
    largest = [dict(r) for r in c.execute("""SELECT family_id,count(*) size FROM evidence_family_members
                                             GROUP BY family_id ORDER BY size DESC,family_id LIMIT 10""")]
    return {"by_representation": by_rep,
            "evidence_count": c.execute("SELECT count(*) FROM evidence_chunks").fetchone()[0],
            "searchable_count": c.execute("SELECT count(*) FROM evidence_chunks WHERE searchable=1").fetchone()[0],
            "quarantined_count": c.execute("SELECT count(*) FROM evidence_chunks WHERE searchable=0").fetchone()[0],
            "family_count": c.execute("SELECT count(*) FROM evidence_families").fetchone()[0],
            "fact_count": c.execute("SELECT count(*) FROM evidence_facts").fetchone()[0],
            "equivalent_count": c.execute("SELECT count(*) FROM evidence_family_members WHERE exact_duplicate_of IS NOT NULL").fetchone()[0],
            "conflict_count": c.execute("SELECT count(*) FROM evidence_families WHERE conflict_status='conflicted'").fetchone()[0],
            "evidence_kinds": kinds, "family_types": types, "fact_fields": fact_fields, "largest_families": largest}
