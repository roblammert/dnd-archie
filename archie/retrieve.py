from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable

from .config import settings
from .db import connect
from .source import load_manifest, verify_source


@dataclass
class Evidence:
    evidence_id: str
    page_pdf: int
    page_label: str
    heading: str
    text: str
    score: float
    role: str = "primary"

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Concept:
    key: str
    triggers: tuple[str, ...]
    queries: tuple[str, ...]
    markers: tuple[str, ...] = ()
    preferred_sections: tuple[str, ...] = ()


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
    "can", "could", "did", "do", "does", "for", "from", "had", "has", "have",
    "how", "i", "if", "in", "into", "is", "it", "me", "my", "of", "on", "or",
    "that", "the", "their", "them", "then", "there", "these", "they", "this",
    "those", "to", "was", "were", "what", "when", "where", "which", "who", "why",
    "will", "with", "would", "you", "your", "happen", "happens", "happened",
}

# These aliases interpret player language only. They are retrieval hints, never rules authority.
ALIASES = {
    "armor number": "armor class",
    "armour number": "armor class",
    "defense number": "armor class",
    "defence number": "armor class",
    "sneak past": "hide stealth",
    "sneaking past": "hide stealth",
    "sneak by": "hide stealth",
    "spell dc": "spell save dc",
    "passive perc": "passive perception",
}

CONCEPTS: tuple[Concept, ...] = (
    Concept("advantage", ("advantage",), ("advantage", "roll two d20s"), ("Advantage/Disadvantage", "Advantage ["), ("Playing the Game", "Rules Glossary")),
    Concept("prone", ("prone",), ("prone condition", "prone"), ("Prone [Condition]",), ("Rules Glossary",)),
    Concept("restrained", ("restrained",), ("restrained condition", "restrained"), ("Restrained [Condition]",), ("Rules Glossary",)),
    Concept("invisible", ("invisible", "invisibility"), ("invisible condition", "invisible"), ("Invisible [Condition]",), ("Rules Glossary",)),
    Concept("grappled", ("grappled", "grapple"), ("grappled condition", "grappled"), ("Grappled [Condition]",), ("Rules Glossary",)),
    Concept("concentration", ("concentration", "concentrate"), ("concentration",), ("Concentration Some spells",), ("Rules Glossary",)),
    Concept("help", ("help action", "take the help", "help another", "help"), ("help action",), ("Help [Action]",), ("Rules Glossary",)),
    Concept("saving_throw", ("saving throw", "save"), ("saving throw",), ("Saving Throws", "Save Save is another name"), ("Playing the Game", "Rules Glossary")),
    Concept("ability_check", ("ability check", "ability checks"), ("ability check",), ("Ability Checks",), ("Playing the Game",)),
    Concept("armor_class", ("armor class", "armour class", "ac", "armor number", "armour number", "defense number", "defence number"), ("armor class",), ("Armor Class A creature’s Armor Class represents", "Armor Class represents how well"), ("Playing the Game", "Rules Glossary")),
    Concept("passive_perception", ("passive perception", "passive perc"), ("passive perception",), ("Passive Perception",), ("Character Creation", "Rules Glossary")),
    Concept("spell_save_dc", ("spell save dc", "spell dc", "save dc"), ("spell save dc",), ("Spell save DC =", "calculate the DC for your spells"), ("Character Creation", "Spells")),
    Concept("hide", ("hide action", "hide", "stealth", "sneak", "sneaking"), ("hide action", "dexterity stealth"), ("Hide [Action]",), ("Rules Glossary",)),
    Concept("movement", ("move before", "move after", "movement", "break up", "between attacks"), ("breaking up your move", "move on your turn"), ("Breaking Up Your Move",), ("Playing the Game", "Rules Glossary")),
    Concept("jump", ("jump", "long jump", "high jump"), ("long jump", "high jump"), ("Long Jump", "High Jump"), ("Rules Glossary",)),
    Concept("spell_per_turn", ("two leveled spells", "two levelled spells", "two spells", "leveled spell", "levelled spell", "spell slot on the same turn"), ("one spell with a spell slot", "spell slot per turn"), (), ("Playing the Game", "Rules Glossary")),
)


def _normalized(q: str) -> str:
    s = q.lower().replace("’", "'")
    for src, dst in ALIASES.items():
        s = s.replace(src, dst)
    return re.sub(r"\s+", " ", s).strip()


def _terms(q: str) -> list[str]:
    raw = re.findall(r"[A-Za-z0-9']+", _normalized(q))
    useful = [t for t in raw if len(t) > 1 and t not in STOPWORDS]
    if not useful:
        useful = raw
    return list(dict.fromkeys(useful))


def _quote(term: str) -> str:
    return f'"{term.replace(chr(34), chr(34) * 2)}"'


def _fts_query(q: str) -> str:
    return " OR ".join(_quote(t) for t in _terms(q)[:20])


def _phrase_query(phrases: Iterable[str]) -> str:
    clean = [p.strip().lower() for p in phrases if p.strip()]
    return " OR ".join(_quote(p) for p in clean)


def detect_concepts(query: str) -> list[Concept]:
    q = _normalized(query)
    found: list[Concept] = []
    for concept in CONCEPTS:
        if any(trigger in q for trigger in concept.triggers):
            found.append(concept)
    return found


def _open_verified_db():
    verify_source()
    if not settings.database.exists():
        raise RuntimeError("SRD index not found. Run: python -m archie.cli ingest")
    c = connect()
    meta = dict(c.execute("SELECT key,value FROM metadata").fetchall())
    expected = load_manifest()["sha256"]
    if meta.get("source_sha256") != expected:
        c.close()
        raise RuntimeError("SRD index does not match the approved source. Run: python -m archie.cli ingest")
    return c


def _raw_search(c, iq: str, limit: int = 24):
    if not iq:
        return []
    return c.execute(
        """
        SELECT c.id,c.evidence_id,c.page_pdf,c.page_label,c.heading,c.text,
               bm25(chunks_fts, 0.0, 3.0, 1.0) AS rank
        FROM chunks_fts JOIN chunks c ON c.id=chunks_fts.rowid
        WHERE chunks_fts MATCH ?
        ORDER BY rank LIMIT ?
        """,
        (iq, limit),
    ).fetchall()


def _row_to_evidence(row, role: str = "primary", score_adjust: float = 0.0) -> Evidence:
    return Evidence(
        row["evidence_id"], row["page_pdf"], row["page_label"], row["heading"],
        row["text"], float(row["rank"]) + score_adjust, role,
    )


def _concept_priority(row, concept: Concept) -> tuple:
    text = row["text"]
    lower = text.lower()
    marker_positions = [lower.find(m.lower()) for m in concept.markers if m.lower() in lower]
    marker_pos = min(marker_positions) if marker_positions else 10**9
    marker_hit = 0 if marker_positions else 1
    section_hit = 0 if any(s.lower() == row["heading"].lower() for s in concept.preferred_sections) else 1
    # Definition markers and canonical sections outrank raw BM25 for concept lookups.
    return (marker_hit, section_hit, marker_pos, float(row["rank"]))


def _best_for_concept(c, concept: Concept):
    rows = _raw_search(c, _phrase_query(concept.queries), 32)
    if not rows:
        return None
    return min(rows, key=lambda r: _concept_priority(r, concept))


def _neighbors(c, rowid: int):
    return c.execute(
        """
        SELECT id,evidence_id,page_pdf,page_label,heading,text,0.0 AS rank
        FROM chunks
        WHERE id IN (?, ?)
        ORDER BY id
        """,
        (rowid - 1, rowid + 1),
    ).fetchall()


def search(query: str, top_k: int | None = None) -> list[Evidence]:
    """Deterministic Retrieval v2.

    1. Detect canonical SRD concepts from the player's wording.
    2. Guarantee a definition-shaped candidate for each detected concept when available.
    3. Fill remaining primary slots with normalized BM25 retrieval.
    4. Add document-order neighbors around the strongest primary hits, including page breaks.
    """
    limit = top_k or settings.top_k
    if limit <= 0:
        return []

    c = _open_verified_db()
    try:
        concepts = detect_concepts(query)
        selected: list[tuple[object, str]] = []
        seen: set[str] = set()

        # Multi-concept decomposition: reserve at least one strong hit per concept.
        for concept in concepts:
            row = _best_for_concept(c, concept)
            if row is not None and row["evidence_id"] not in seen:
                selected.append((row, "concept"))
                seen.add(row["evidence_id"])

        # General lexical recall still matters for names, spells, equipment, and unforeseen queries.
        general_query = _fts_query(query)
        for row in _raw_search(c, general_query, max(24, limit * 4)):
            if row["evidence_id"] not in seen:
                selected.append((row, "primary"))
                seen.add(row["evidence_id"])
            if len(selected) >= max(limit, 6):
                break

        if not selected:
            return []

        # Preserve all concept hits first. Then include top lexical hits.
        primaries = selected[:limit]
        out: list[Evidence] = [_row_to_evidence(row, role) for row, role in primaries]
        out_seen = {e.evidence_id for e in out}

        # Cross-page neighbor expansion. Use spare packet slots only; never evict a concept hit.
        # Expanding the first 3 strong hits is enough to bridge most rule/page boundaries.
        if len(out) < limit:
            for row, _role in primaries[:3]:
                for n in _neighbors(c, int(row["id"])):
                    if n["evidence_id"] in out_seen:
                        continue
                    out.append(_row_to_evidence(n, "context", score_adjust=1000.0))
                    out_seen.add(n["evidence_id"])
                    if len(out) >= limit:
                        break
                if len(out) >= limit:
                    break

        return out[:limit]
    finally:
        c.close()


def retrieval_debug(query: str, top_k: int | None = None) -> dict:
    concepts = detect_concepts(query)
    evidence = search(query, top_k)
    return {
        "query": query,
        "normalized": _normalized(query),
        "fts_query": _fts_query(query),
        "concepts": [c.key for c in concepts],
        "top_k": top_k or settings.top_k,
        "evidence": [e.to_dict() for e in evidence],
    }


def evidence_packet(items: list[Evidence]) -> str:
    parts = []
    for e in items:
        parts.append(
            f"[{e.evidence_id}] PDF page {e.page_pdf} | {e.heading} | retrieval={e.role}\n{e.text}"
        )
    return "\n\n---\n\n".join(parts)
