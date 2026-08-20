from __future__ import annotations

import hashlib
import re
import time

from dataclasses import asdict, dataclass, field

from .concepts import ALIASES, CONCEPTS
from .config import settings
from .db import connect
from .source import get_source_manifest, verify_source
from .evidence_selection import rank_evidence


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
    "happen",
    "happens",
    "happened",
    "right",
    "work",
    "works",
    "working",
    "thing",
    "things",
    "specific",
    "rules",
    "rule",
}


OFFICIAL_AUTHORITIES = {
    "official_srd",
}

SUPPLEMENTAL_AUTHORITIES = {
    "approved_supplement",
}

# Query aliases are deliberately limited to unambiguous structured stat fields.
# Values use evidence_families.semantic_key spelling after underscore folding.
FIELD_QUERY_ALIASES = {
    "hp": "hit points",
    "ac": "armor class",
    "cr": "challenge rating",
}

# Bare exact-name lookup uses this ordering only inside the exact-name candidate
# set. It does not alter FTS/family scores; explicit type/table language wins.
BARE_ENTITY_TYPE_PRIORITY = {
    "class": 5.0,
    "subclass": 5.0,
    "monster": 4.0,
    "species": 4.0,
    "spell": 4.0,
    "background": 3.0,
    "feat": 3.0,
    "equipment": 2.0,
    "magic-item": 1.0,
}


@dataclass
class Evidence:
    evidence_id: str
    page_pdf: int | None
    page_label: str | None
    heading: str
    text: str
    score: float

    source_id: str = "srd521"
    authority_type: str = "official_srd"
    edition: str | None = "2024"

    origin: str = "primary"
    matched_by: list[str] = field(default_factory=list)

    content_type: str | None = None
    record_name: str | None = None
    source_priority: int = 0
    authority_id: str | None = None
    representation_id: str | None = None
    canonical_entity_id: str | None = None
    evidence_family_id: str | None = None
    evidence_kind: str | None = None
    conflict_status: str = "clear"

    def to_dict(self):
        return asdict(self)


@dataclass
class QueryPlan:
    original: str
    terms: list[str]
    concepts: list[str]
    aliases: list[str]
    subqueries: list[str]
    intent: str = "general"
    entity_names: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def _tokens(q: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", q.lower())


def _find_aliases(q: str) -> list[str]:
    lower = q.lower()

    found = []

    for alias, expansions in ALIASES.items():
        if alias in lower:
            found.extend(expansions)

    return list(dict.fromkeys(found))


def _find_concepts(
    q: str,
    alias_expansions: list[str],
) -> list[str]:
    lower = q.lower()

    found = []

    for key in sorted(
        CONCEPTS,
        key=len,
        reverse=True,
    ):
        if re.search(
            rf"\b{re.escape(key)}\b",
            lower,
        ):
            found.append(key)

    for expansion in alias_expansions:
        if (
            expansion in CONCEPTS
            and expansion not in found
        ):
            found.append(expansion)

    # Comparison questions need independent representation
    # of both sides.
    if (
        "saving throw" in lower
        and "ability check" in lower
    ):
        for concept in (
            "ability check",
            "saving throw",
        ):
            if concept not in found:
                found.append(concept)

    return found


def build_query_plan(q: str) -> QueryPlan:
    aliases = _find_aliases(q)
    lower = q.lower()

    for alias, semantic_key in FIELD_QUERY_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lower) and semantic_key not in aliases:
            aliases.append(semantic_key)

    # Deterministic intent bridges for common
    # natural-language phrasing.
    if (
        "move" in lower
        and "before" in lower
        and "after" in lower
        and "breaking up your move" not in aliases
    ):
        aliases.append(
            "breaking up your move"
        )

    if (
        "leveled spell" in lower
        or "levelled spell" in lower
    ):
        if "spell slot per turn" not in aliases:
            aliases.append(
                "spell slot per turn"
            )

    if (
        "natural 20" in lower
        and "natural 20" not in aliases
    ):
        aliases.append("natural 20")

    if (
        "natural 1" in lower
        and "natural 1" not in aliases
    ):
        aliases.append("natural 1")

    concepts = _find_concepts(
        q,
        aliases,
    )

    terms = [
        token
        for token in _tokens(q)
        if (
            len(token) > 1
            and token not in STOPWORDS
        )
    ]

    for expansion in aliases:
        terms.extend(
            _tokens(expansion)
        )

    for concept in concepts:
        terms.extend(
            _tokens(
                CONCEPTS[concept]["canonical"]
            )
        )

    terms = list(
        dict.fromkeys(
            term
            for term in terms
            if term not in STOPWORDS
        )
    )

    if not terms:
        terms = list(
            dict.fromkeys(
                _tokens(q)
            )
        )

    subqueries = []

    for concept in concepts:
        subqueries.append(
            CONCEPTS[concept]["canonical"]
        )

    subqueries.extend(aliases)

    subqueries = list(
        dict.fromkeys(subqueries)
    )

    return QueryPlan(
        original=q,
        terms=terms[:24],
        concepts=concepts,
        aliases=aliases,
        subqueries=subqueries,
        intent=_query_intent(q),
    )


def _query_intent(q: str) -> str:
    """Small, deterministic evidence-kind heuristic; uncertainty stays general."""
    lower = q.lower()
    if re.search(r"\b(table|chart|list|progression)\b", lower):
        return "table"
    if re.search(r"\b(features?|subclass features?|class features?)\b", lower):
        return "feature"
    if re.search(r"\b(range|casting time|duration|damage|cost|weight|armor class|\bac\b|hit points|\bhp\b|speed)\b", lower):
        return "field"
    if re.search(r"\b(explain|explanation|how does|what happens|why|describe)\b", lower):
        return "explanation"
    return "general"


def _requested_field_keys(q: str) -> set[str]:
    """Return explicit structured-field requests; aliases never cross fields."""
    lower = q.lower()
    requested = {
        key.replace("_", " ")
        for key in (
            "range", "casting_time", "duration", "damage", "cost", "weight",
            "armor_class", "hit_points", "hit_point_formula", "speed", "school",
            "level", "challenge_rating", "components",
        )
        if re.search(rf"\b{re.escape(key.replace('_', ' '))}\b", lower)
    }
    for alias, semantic_key in FIELD_QUERY_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lower):
            requested.add(semantic_key)
    return requested


def _entity_type(entity_id: str | None) -> str | None:
    if not entity_id:
        return None
    parts = entity_id.split("/")
    return parts[1] if len(parts) > 2 else None


def _requested_entity_types(q: str) -> set[str]:
    """Small deterministic type vocabulary; no fuzzy or inferred identity."""
    lower = q.lower()
    cues = (
        (r"\b(monsters?|creatures?)\b", "monster"),
        (r"\bspells?\b", "spell"),
        (r"\b(species|races?)\b", "species"),
        (r"\bsubclasses?\b", "subclass"),
        (r"\bclasses?\b", "class"),
        (r"\bfeats?\b", "feat"),
        (r"\bmagic items?\b", "magic-item"),
        (r"\b(weapons?|equipment)\b", "equipment"),
        (r"\b(actions?)\b", "action"),
        (r"\brules?\b", "rule"),
    )
    return {entity_type for pattern, entity_type in cues if re.search(pattern, lower)}


def _escape(term: str) -> str:
    return term.replace(
        '"',
        '""',
    )


def _add_exact_entity_subqueries(c, plan: QueryPlan) -> None:
    """Add canonical display names explicitly present in the query; never fuzzy."""
    lower = plan.original.lower()
    normalized_query = re.sub(r"[^a-z0-9]+", " ", lower).strip()
    names = []
    exact_types = set()
    field_labels = {"armor class", "hit points", "casting time", "range", "duration",
                    "components", "damage", "cost", "weight", "speed", "school", "level"}
    for row in c.execute("SELECT DISTINCT display_name,entity_type FROM canonical_entities ORDER BY length(display_name) DESC,display_name"):
        name = (row["display_name"] or "").strip()
        normalized_name = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
        alternate = ""
        if "," in name:
            base, qualifier = (part.strip().lower() for part in name.split(",", 1))
            alternate = f"{qualifier} {base}"
        if normalized_name not in field_labels and len(name) >= 3 and (
            re.search(rf"\b{re.escape(name.lower())}\b", lower)
            or normalized_name == normalized_query
            or alternate == normalized_query
        ):
            names.append(name.lower())
            if normalized_name == normalized_query or alternate == normalized_query:
                exact_types.add(row["entity_type"])
    plan.entity_names = list(dict.fromkeys(names))[:8]
    exact_bare_name = normalized_query in {
        re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
        for name in plan.entity_names
    }
    # Only bare exact-name and explicitly type-qualified lookups move ahead of
    # historical concept bridges. Ordinary core-rule queries keep PDF fallback
    # reservation behavior unchanged.
    if ((exact_bare_name and len(exact_types) > 1)
            or _requested_entity_types(plan.original)
            or _requested_field_keys(plan.original)):
        plan.subqueries = list(dict.fromkeys(plan.entity_names + plan.subqueries))
    else:
        plan.subqueries = list(dict.fromkeys(plan.subqueries + plan.entity_names))


def _fts_or(
    terms: list[str],
) -> str:
    return " OR ".join(
        f'"{_escape(term)}"'
        for term in terms
        if term
    )


def _authority_placeholders(
    authority_types: set[str],
) -> str:
    return ",".join(
        "?"
        for _ in authority_types
    )


def _fetch_fts(
    c,
    query: str,
    limit: int,
    *,
    authority_types: set[str] | None = None,
    evidence_kinds: set[str] | None = None,
):
    """
    Retrieve candidates from enabled, approved, licensed
    sources in the active edition.

    Alpha.5 deliberately allows callers to retrieve official
    and supplemental authority pools independently. This keeps
    supplemental content from consuming the entire final
    evidence budget before canonical SRD evidence has had a
    chance to participate.
    """

    if not query:
        return []

    params: list[object] = [
        query,
        settings.active_edition,
    ]

    authority_clause = ""
    kind_clause = ""

    if authority_types:
        ordered = sorted(
            authority_types
        )

        placeholders = (
            _authority_placeholders(
                set(ordered)
            )
        )

        authority_clause = (
            f" AND s.authority_type "
            f"IN ({placeholders})"
        )

        params.extend(ordered)

    if evidence_kinds:
        kinds = sorted(evidence_kinds)
        kind_clause = f" AND c.evidence_kind IN ({','.join('?' for _ in kinds)})"
        params.extend(kinds)

    params.append(limit)

    sql = f"""
      SELECT
          c.id,
          c.evidence_id,
          c.source_id,
          c.page_pdf,
          c.page_label,
          c.heading,
          c.text,
          c.content_record_id,
          cr.content_type,
          cr.name AS record_name,
          s.authority_type,
          s.authority_id,
          s.representation_id,
          s.edition,
          s.priority,
          c.evidence_kind,
          bm25(
              evidence_fts,
              0.0,
              3.0,
              1.0
          ) AS rank
      FROM evidence_fts
      JOIN evidence_chunks c
          ON c.id = evidence_fts.rowid
      JOIN sources s
          ON s.id = c.source_id
      LEFT JOIN content_records cr
          ON cr.id = c.content_record_id
      WHERE
          evidence_fts MATCH ?
          AND s.enabled = 1
          AND s.approved = 1
          AND s.license_status = 'present'
          AND (
              s.edition IS NULL
              OR s.edition = ?
          )
          {authority_clause}
          {kind_clause}
      ORDER BY rank
      LIMIT ?
    """

    rows = c.execute(
        sql,
        tuple(params),
    ).fetchall()
    if not rows:
        return []

    # Load family metadata once after FTS has limited raw chunks. Joining the
    # many-family relation inside the FTS query multiplies rows before LIMIT and
    # is particularly expensive for broad structured-record matches.
    ids = [row["id"] for row in rows]
    placeholders = ",".join("?" for _ in ids)
    memberships = {}
    for member in c.execute(f"""SELECT m.evidence_chunk_id,m.family_id,m.normalized_digest,
                                        f.canonical_entity_id,f.conflict_status,f.family_type,f.semantic_key
                                 FROM evidence_family_members m JOIN evidence_families f ON f.id=m.family_id
                                 WHERE m.evidence_chunk_id IN ({placeholders})
                                 ORDER BY m.evidence_chunk_id,m.family_id""", ids):
        memberships.setdefault(member["evidence_chunk_id"], []).append(dict(member))
    expanded = []
    empty = {"family_id": None, "normalized_digest": None, "canonical_entity_id": None,
             "conflict_status": None, "family_type": None, "semantic_key": None}
    for row in rows:
        base = dict(row)
        for member in memberships.get(row["id"], [empty]):
            expanded.append(base | member)
    return expanded


def _score_row(
    row,
    plan: QueryPlan,
    matched_by: str,
) -> float:
    text = row["text"].lower()
    heading = row["heading"]

    score = max(
        0.0,
        -float(row["rank"]),
    )

    record_name = (row["record_name"] or "").strip().lower()
    if record_name and re.search(rf"\b{re.escape(record_name)}\b", plan.original.lower()):
        score += 6.0
    if "," in record_name:
        base, qualifier = (part.strip() for part in record_name.split(",", 1))
        reordered = f"{qualifier} {base}"
        if reordered and re.search(rf"\b{re.escape(reordered)}\b", plan.original.lower()):
            score += 10.0
    # Preserve explicit enhancement modifiers that the general token filter
    # intentionally drops as one-character terms (for example, +1/+2/+3).
    requested_modifiers = set(re.findall(r"\+\s*([0-9]+)\b", plan.original.lower()))
    record_modifiers = set(re.findall(r"\+\s*([0-9]+)\b", record_name))
    if requested_modifiers and record_modifiers:
        score += 8.0 if requested_modifiers & record_modifiers else -4.0

    for term in plan.terms:
        if term in text:
            score += min(
                1.2,
                text.count(term) * 0.15,
            )

    for concept in plan.concepts:
        meta = CONCEPTS[concept]
        canonical = (
            meta["canonical"]
            .lower()
        )

        if canonical in text:
            score += 4.0

        marker = meta.get("marker")

        if (
            marker
            and marker.lower() in text
        ):
            score += 12.0

        if heading in meta.get(
            "sections",
            (),
        ):
            score += 4.0

        # Named glossary definitions receive a modest
        # deterministic boost.
        if re.search(
            rf"\b{re.escape(canonical)}\b"
            rf"(?:\s*\[[^\]]+\])?",
            text,
        ):
            score += 1.5

    if matched_by.startswith(
        "exact:"
    ):
        score += 5.0

    return score


def _read_index_identity(c) -> dict:
    """
    Read the compatibility identity metadata used by the
    historical v1.x integrity contract.
    """

    return dict(
        c.execute(
            """
            SELECT key, value
            FROM metadata
            WHERE key IN (
                'source_id',
                'source_sha256',
                'source_version',
                'schema_version'
            )
            """
        ).fetchall()
    )


def _active_source_identity(
    c,
    source_id: str,
):
    """
    Read the canonical generated Source Library identity for an
    active source version.

    This does not replace the compatibility metadata check. It
    provides a second independent integrity observation used for
    diagnostics and transient-read detection.
    """

    return c.execute(
        """
        SELECT
            s.id AS source_id,
            sv.version,
            sv.content_sha256
        FROM sources s
        JOIN source_versions sv
          ON sv.source_id = s.id
         AND sv.active = 1
        WHERE s.id = ?
        """,
        (
            source_id,
        ),
    ).fetchone()


def _index_identity_matches(
    metadata: dict,
    *,
    source_id: str,
    source_sha256: str,
) -> bool:
    return (
        metadata.get("source_id")
        == source_id
        and metadata.get(
            "source_sha256"
        )
        == source_sha256
    )


def _verify_index(c):
    """
    Verify that generated retrieval storage still corresponds to
    the approved canonical SRD.

    Historical Archie releases intentionally bind the compatibility
    metadata table to the canonical SRD hash. That contract remains
    intact.

    Alpha.5 adds one bounded reread because the live sequential
    regression exposed a single transient identity mismatch that
    immediately disappeared on the next request.

    A persistent mismatch still fails closed. No automatic ingest,
    metadata rewrite, or self-healing is performed here.
    """

    manifest = get_source_manifest(
        settings.source_id
    )

    expected_id = manifest.id
    expected_sha256 = (
        manifest.sha256
    )

    metadata = (
        _read_index_identity(c)
    )

    if _index_identity_matches(
        metadata,
        source_id=expected_id,
        source_sha256=expected_sha256,
    ):
        return

    # Cross-check the normalized Source Library before doing the
    # bounded reread. This gives a useful distinction between a
    # transient compatibility-metadata observation and a genuinely
    # wrong generated database.
    active = _active_source_identity(
        c,
        expected_id,
    )

    active_matches = (
        active is not None
        and active["source_id"]
        == expected_id
        and active["content_sha256"]
        == expected_sha256
    )

    # One short bounded reread is allowed only when the normalized
    # active source/version is itself correct.
    #
    # This does NOT repair a bad index. Persistent metadata
    # corruption still fails below.
    if active_matches:
        time.sleep(0.05)

        metadata = (
            _read_index_identity(c)
        )

        if _index_identity_matches(
            metadata,
            source_id=expected_id,
            source_sha256=expected_sha256,
        ):
            return

    actual_id = metadata.get(
        "source_id",
        "<missing>",
    )

    actual_sha = metadata.get(
        "source_sha256",
        "<missing>",
    )

    raise RuntimeError(
        "SRD index does not match the approved source. "
        f"expected source_id={expected_id} "
        f"sha256={expected_sha256}; "
        f"index source_id={actual_id} "
        f"sha256={actual_sha}. "
        "Run: python -m archie.cli ingest"
    )
def _collect_candidates(
    c,
    plan: QueryPlan,
    *,
    authority_types: set[str],
    candidate_k: int,
):
    """
    Build a ranked candidate pool for one authority class.

    Query planning and exact concept/alias searches happen
    independently inside each authority pool so that enabling
    a supplemental source cannot erase historical canonical
    concept coverage.
    """

    candidates = {}

    broad = _fts_or(
        plan.terms
    )

    for row in _fetch_fts(
        c,
        broad,
        candidate_k,
        authority_types=authority_types,
    ):
        key = (row["id"], row["family_id"] or "")
        candidates[key] = (
            row,
            _score_row(
                row,
                plan,
                "broad",
            ),
            ["broad"],
        )

    # Table intent gets one bounded, kind-filtered candidate load. Without it,
    # broad structured-record matches can consume LIMIT before eligible tables
    # are visible. This is a single query, not per-family/entity expansion.
    if plan.intent == "table":
        for row in _fetch_fts(
            c, broad, candidate_k,
            authority_types=authority_types,
            evidence_kinds={"table"},
        ):
            key = (row["id"], row["family_id"] or "")
            score = _score_row(row, plan, "kind:table")
            old = candidates.get(key)
            candidates[key] = (
                row,
                max(old[1], score) if old else score,
                list(dict.fromkeys((old[2] if old else []) + ["kind:table"])),
            )

    for subquery in plan.subqueries:
        phrase = (
            '"'
            + _escape(
                subquery.lower()
            )
            + '"'
        )

        tag = f"exact:{subquery}"

        for row in _fetch_fts(
            c,
            phrase,
            candidate_k,
            authority_types=authority_types,
        ):
            score = _score_row(
                row,
                plan,
                tag,
            )

            key = (row["id"], row["family_id"] or "")
            old = candidates.get(key)

            if old:
                candidates[key] = (
                    row,
                    max(
                        old[1],
                        score,
                    ),
                    list(
                        dict.fromkeys(
                            old[2]
                            + [tag]
                        )
                    ),
                )
            else:
                candidates[key] = (
                    row,
                    score,
                    [tag],
                )

    return sorted(
        candidates.values(),
        key=lambda item: (
            -item[1],
            item[0]["id"],
        ),
    )


def _select_pool(
    ranked,
    plan: QueryPlan,
    limit: int,
):
    """
    Select candidates from a single authority pool.

    One exact hit is reserved for each planned concept/alias
    whenever possible. This preserves the historical comparison
    behavior for questions such as ability check vs saving throw.
    """

    if limit <= 0:
        return []

    selected = []
    selected_ids = set()

    for subquery in plan.subqueries:
        if len(selected) >= limit:
            break

        tag = f"exact:{subquery}"

        exact = [
            item
            for item in ranked
            if (
                tag in item[2]
                and item[0]["id"]
                not in selected_ids
            )
        ]

        if exact:
            chosen = exact[0]

            selected.append(
                chosen
            )

            selected_ids.add(
                chosen[0]["id"]
            )

    for item in ranked:
        if len(selected) >= limit:
            break

        row = item[0]

        if row["id"] in selected_ids:
            continue

        selected.append(item)

        selected_ids.add(
            row["id"]
        )

    return selected


def _merge_authority_candidates(
    official_ranked,
    supplemental_ranked,
    plan: QueryPlan,
    top_k: int,
):
    """
    Merge canonical and supplemental candidate pools.

    Alpha.5 invariant:

        Supplemental sources may fill gaps.
        They must not make canonical SRD retrieval worse.

    For the normal 12-item evidence budget, up to eight primary
    slots are reserved for official evidence and up to four for
    supplemental evidence.

    Unused capacity flows to whichever side has additional
    candidates, so supplemental-only questions can still use the
    full evidence budget.
    """

    if top_k <= 0:
        return []

    # Roughly two thirds of the final primary window is reserved
    # for official evidence when official candidates exist.
    official_target = min(
        len(official_ranked),
        max(
            1,
            (top_k * 2 + 2) // 3,
        ),
    )

    supplemental_target = min(
        len(supplemental_ranked),
        max(
            0,
            top_k - official_target,
        ),
    )

    official_selected = _select_pool(
        official_ranked,
        plan,
        official_target,
    )

    supplemental_selected = _select_pool(
        supplemental_ranked,
        plan,
        supplemental_target,
    )

    selected = (
        official_selected
        + supplemental_selected
    )

    selected_ids = {
        item[0]["id"]
        for item in selected
    }

    remaining = (
        top_k
        - len(selected)
    )

    if remaining > 0:
        leftovers = []

        for item in official_ranked:
            if (
                item[0]["id"]
                not in selected_ids
            ):
                leftovers.append(item)

        for item in supplemental_ranked:
            if (
                item[0]["id"]
                not in selected_ids
            ):
                leftovers.append(item)

        # Relevance determines how unused capacity is filled.
        # Authority quotas have already been satisfied above.
        leftovers.sort(
            key=lambda item: (
                -item[1],
                -int(
                    item[0]["priority"]
                    or 0
                ),
                item[0]["id"],
            )
        )

        for item in leftovers:
            if remaining <= 0:
                break

            if (
                item[0]["id"]
                in selected_ids
            ):
                continue

            selected.append(item)

            selected_ids.add(
                item[0]["id"]
            )

            remaining -= 1

    return selected[:top_k]


def _candidate_to_evidence(
    item,
) -> Evidence:
    row, score, matched = item

    return Evidence(
        evidence_id=row["evidence_id"],
        page_pdf=row["page_pdf"],
        page_label=row["page_label"],
        heading=row["heading"],
        text=row["text"],
        score=score,
        source_id=row["source_id"],
        authority_type=row[
            "authority_type"
        ],
        edition=row["edition"],
        origin="primary",
        matched_by=matched,
        content_type=row[
            "content_type"
        ],
        record_name=row[
            "record_name"
        ],
        source_priority=int(
            row["priority"]
            or 0
        ),
        authority_id=row["authority_id"],
        representation_id=row["representation_id"],
        canonical_entity_id=row["canonical_entity_id"],
        evidence_family_id=row["family_id"],
        evidence_kind=row["evidence_kind"],
        conflict_status=row["conflict_status"],
    )


def _family_aware_select(ranked, plan: QueryPlan, top_k: int):
    """Budget families, never representation matches; choose one suited member."""
    requested_fields = _requested_field_keys(plan.original)
    requested_types = _requested_entity_types(plan.original)
    normalized_query = re.sub(r"[^a-z0-9]+", " ", plan.original.lower()).strip()
    bare_exact = normalized_query in {
        re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
        for name in plan.entity_names
    }
    families = {}
    progression_table_requested = (
        plan.intent == "table"
        and bool(re.search(r"\b(?:class\s+table|progression)\b", plan.original.lower()))
    )
    for item in ranked:
        row, score, matched = item
        semantic_key = (row["semantic_key"] or "").replace("_", " ").lower()
        semantic_requested = bool(
            semantic_key
            and (semantic_key in requested_fields
                 or re.search(rf"\b{re.escape(semantic_key)}\b", plan.original.lower()))
        )
        # A retained field discrepancy blocks only a query that requests that
        # field. It must not poison unrelated claims about the same entity.
        if row["conflict_status"] == "conflicted" and not semantic_requested:
            continue
        if semantic_requested:
            score += 8.0
            item = (row, score, matched)
        preferred_family = {
            "field": "field", "explanation": "prose_rule",
            "table": "table", "feature": "feature",
        }.get(plan.intent)
        if preferred_family and row["family_type"] == preferred_family:
            score += 12.0 if plan.intent == "feature" else 6.0
            item = (row, score, matched)
        if progression_table_requested and row["family_type"] == "table":
            table_text = (row["text"] or "").lower()
            if (
                '"level"' in table_text
                and '"proficiency bonus"' in table_text
                and '"class features"' in table_text
            ):
                score += 30.0
            item = (row, score, matched)
        entity_id = row["canonical_entity_id"] or ""
        entity_type = _entity_type(entity_id)
        if entity_type in requested_types:
            score += 6.0
            item = (row, score, matched)
        key = row["family_id"] or f"isolated:{row['representation_id']}:{row['evidence_id']}"
        families.setdefault(key, []).append(item)

    selected_families = []
    for key, members in families.items():
        ranked_members = rank_evidence([
            {
                "item": item,
                "evidence_id": item[0]["evidence_id"],
                "evidence_kind": item[0]["evidence_kind"],
                "text_length": len(item[0]["text"] or ""),
                "normalized_digest": item[0]["normalized_digest"] or "",
                "representation_id": item[0]["representation_id"],
            }
            for item in members
        ], plan.intent)
        chosen = ranked_members[0]["item"]
        family_score = max(item[1] for item in members)
        # Member kind controls selection; family relevance is still its best FTS hit.
        chosen = (chosen[0], family_score, chosen[2])
        entity = chosen[0]["canonical_entity_id"] or key
        selected_families.append((chosen, entity, key))

    selected_families.sort(key=lambda value: (-value[0][1], value[2], value[0][0]["evidence_id"]))
    if top_k <= 0:
        return []

    # When alternatives exist, no canonical entity may consume the full budget.
    entity_count = len({value[1] for value in selected_families})
    entity_cap = top_k if entity_count <= 1 else max(1, (top_k + 1) // 2)
    focus_entity = None
    if selected_families:
        top_row = selected_families[0][0][0]
        normalized_name = re.sub(r"[^a-z0-9]+", " ", (top_row["record_name"] or "").lower()).strip()
        if normalized_name and normalized_name == normalized_query:
            focus_entity = selected_families[0][1]

    def cap_for(entity):
        return top_k if entity == focus_entity else entity_cap
    counts = {}
    table_counts = {}
    table_cap = top_k if plan.intent == "table" else min(2, entity_cap)
    selected = []
    selected_keys = set()
    deferred = []
    if progression_table_requested:
        progression = next(
            (
                value
                for value in selected_families
                if value[0][0]["family_type"] == "table"
                and '"level"' in (value[0][0]["text"] or "").lower()
                and '"proficiency bonus"' in (value[0][0]["text"] or "").lower()
                and '"class features"' in (value[0][0]["text"] or "").lower()
            ),
            None,
        )
        if progression is not None:
            chosen, entity, key = progression
            selected.append(chosen)
            selected_keys.add(key)
            counts[entity] = 1
            table_counts[entity] = 1
    # Preserve one family for each deterministic exact concept/alias bridge.
    for subquery in plan.subqueries:
        tag = f"exact:{subquery}"
        exact = [value for value in selected_families
                 if value[2] not in selected_keys and tag in value[0][2]]
        requested_field = next((value for value in exact
                                if plan.intent == "field" and value[0][0]["family_type"] == "field"
                                and ((value[0][0]["semantic_key"] or "").replace("_", " ").lower()
                                     in requested_fields
                                     or (value[0][0]["semantic_key"] or "").replace("_", " ").lower()
                                     in plan.original.lower())), None)
        if requested_field:
            match = requested_field
        elif subquery in plan.entity_names:
            named = [value for value in exact
                     if (value[0][0]["record_name"] or "").lower() == subquery
                     and value[0][0]["family_id"] is not None]
            preferred = {"table": "table", "feature": "feature", "explanation": "prose_rule"}.get(plan.intent)
            preferred_match = next((value for value in named if value[0][0]["family_type"] == preferred), None)
            typed_match = next((value for value in named
                                if _entity_type(value[0][0]["canonical_entity_id"]) in requested_types), None)
            bare_match = (max(named, key=lambda value: (
                BARE_ENTITY_TYPE_PRIORITY.get(_entity_type(value[0][0]["canonical_entity_id"]), 0.0),
                value[0][1],
            )) if bare_exact and named else None)
            if preferred:
                # Preserve the historical fall-through: a feature/table/prose
                # family whose record has a different name may win globally.
                match = preferred_match
            else:
                match = (typed_match if requested_types else bare_match if bare_match else
                         (named[0] if named else (exact[0] if exact else None)))
        else:
            # Historical PDF chunks without deterministic family links retain one
            # exact-concept fallback slot (and therefore their neighbor context).
            match = next((value for value in exact
                          if value[0][0]["page_pdf"] is not None and value[0][0]["family_id"] is None),
                         exact[0] if exact else None)
        if match and len(selected) < top_k:
            chosen, entity, key = match
            selected.append(chosen)
            selected_keys.add(key)
            counts[entity] = counts.get(entity, 0) + 1
            if chosen[0]["family_type"] == "table":
                table_counts[entity] = table_counts.get(entity, 0) + 1
    for chosen, entity, key in selected_families:
        if len(selected) >= top_k:
            break
        if key in selected_keys:
            continue
        if counts.get(entity, 0) >= cap_for(entity):
            deferred.append((chosen, entity))
            continue
        if chosen[0]["family_type"] == "table" and table_counts.get(entity, 0) >= table_cap:
            deferred.append((chosen, entity))
            continue
        selected.append(chosen)
        selected_keys.add(key)
        counts[entity] = counts.get(entity, 0) + 1
        if chosen[0]["family_type"] == "table":
            table_counts[entity] = table_counts.get(entity, 0) + 1
    if len(selected) < top_k:
        for chosen, entity in deferred:
            if len(selected) >= top_k:
                break
            selected.append(chosen)
    return selected


def search(
    query: str,
    top_k: int | None = None,
    *,
    expand_neighbors: bool = True,
) -> list[Evidence]:
    verify_source()

    if not settings.database.exists():
        raise RuntimeError(
            "SRD index not found. "
            "Run: python -m archie.cli ingest"
        )

    plan = build_query_plan(
        query
    )

    final_k = (
        top_k
        or settings.top_k
    )

    candidate_k = max(
        settings.retrieval_candidate_k,
        final_k * 5,
    )

    c = connect()

    try:
        _verify_index(c)
        _add_exact_entity_subqueries(c, plan)

        official_ranked = (
            _collect_candidates(
                c,
                plan,
                authority_types=(
                    OFFICIAL_AUTHORITIES
                ),
                candidate_k=candidate_k,
            )
        )

        supplemental_ranked = (
            _collect_candidates(
                c,
                plan,
                authority_types=(
                    SUPPLEMENTAL_AUTHORITIES
                ),
                candidate_k=candidate_k,
            )
        )

        # Legacy authority_type pools are retained only as an input compatibility
        # boundary. All active representations share one authority and are budgeted
        # together by evidence family.
        selected = _family_aware_select(
            official_ranked + supplemental_ranked,
            plan,
            final_k,
        )

        evidence = []
        seen = set()
        primary_ids = []

        for item in selected:
            row = item[0]

            ev = (
                _candidate_to_evidence(
                    item
                )
            )

            evidence.append(ev)

            seen.add(
                row["id"]
            )

            if row["page_pdf"] is not None:
                primary_ids.append(row["id"])

        if (
            expand_neighbors
            and settings.neighbor_radius > 0
        ):
            # Expand only around the strongest few primary hits.
            # Because official evidence is intentionally represented
            # first in the merged primary set, historical SRD context
            # remains stable when supplemental sources are enabled.
            for rid in primary_ids[
                : min(
                    3,
                    len(primary_ids),
                )
            ]:
                rows = c.execute(
                    """
                    SELECT
                        c.id,
                        c.evidence_id,
                        c.source_id,
                        c.page_pdf,
                        c.page_label,
                        c.heading,
                        c.text,
                        cr.content_type,
                        cr.name AS record_name,
                        s.authority_type,
                        s.authority_id,
                        s.representation_id,
                        s.edition,
                        s.priority,
                        c.evidence_kind
                    FROM evidence_chunks c
                    JOIN sources s
                        ON s.id = c.source_id
                    LEFT JOIN content_records cr
                        ON cr.id = c.content_record_id
                    WHERE
                        c.id BETWEEN ? AND ?
                        AND s.enabled = 1
                        AND s.approved = 1
                        AND s.license_status = 'present'
                        AND c.searchable = 1
                        AND c.page_pdf IS NOT NULL
                        AND (
                            s.edition IS NULL
                            OR s.edition = ?
                        )
                    ORDER BY c.id
                    """,
                    (
                        max(
                            1,
                            rid
                            - settings.neighbor_radius,
                        ),
                        rid
                        + settings.neighbor_radius,
                        settings.active_edition,
                    ),
                ).fetchall()

                for row in rows:
                    if row["id"] in seen:
                        continue

                    evidence.append(
                        Evidence(
                            evidence_id=(
                                row["evidence_id"]
                            ),
                            page_pdf=(
                                row["page_pdf"]
                            ),
                            page_label=(
                                row["page_label"]
                            ),
                            heading=(
                                row["heading"]
                            ),
                            text=row["text"],
                            score=-999.0,
                            source_id=(
                                row["source_id"]
                            ),
                            authority_type=(
                                row[
                                    "authority_type"
                                ]
                            ),
                            edition=(
                                row["edition"]
                            ),
                            origin="context",
                            matched_by=[
                                f"neighbor-of:{rid}"
                            ],
                            content_type=(
                                row[
                                    "content_type"
                                ]
                            ),
                            record_name=(
                                row[
                                    "record_name"
                                ]
                            ),
                            source_priority=int(
                                row["priority"]
                                or 0
                            ),
                            authority_id=row["authority_id"],
                            representation_id=row["representation_id"],
                            evidence_kind=row["evidence_kind"],
                        )
                    )

                    seen.add(
                        row["id"]
                    )

        return _dedupe_exact_evidence(
            evidence
        )

    finally:
        c.close()


def _normalized_evidence_text(
    text: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        (text or "")
        .strip()
        .lower(),
    )


def _dedupe_exact_evidence(
    items: list[Evidence],
) -> list[Evidence]:
    """
    Suppress whitespace-equivalent duplicate facts across
    sources.

    If the same normalized text is present from more than one
    source, prefer the higher-authority/higher-priority item,
    then the higher retrieval score.
    """

    grouped: dict[
        str,
        tuple[int, Evidence],
    ] = {}

    unkeyed: list[
        tuple[int, Evidence]
    ] = []

    for index, item in enumerate(
        items
    ):
        key = (
            _normalized_evidence_text(
                item.text
            )
        )

        if not key:
            unkeyed.append(
                (
                    index,
                    item,
                )
            )
            continue

        existing = grouped.get(
            key
        )

        if existing is None:
            grouped[key] = (
                index,
                item,
            )
            continue

        old_index, old_item = (
            existing
        )

        old_rank = (
            1
            if old_item.authority_type
            == "official_srd"
            else 0,
            old_item.source_priority,
            old_item.score,
        )

        new_rank = (
            1
            if item.authority_type
            == "official_srd"
            else 0,
            item.source_priority,
            item.score,
        )

        if new_rank > old_rank:
            grouped[key] = (
                old_index,
                item,
            )

    merged = list(
        grouped.values()
    )

    merged.extend(
        unkeyed
    )

    merged.sort(
        key=lambda pair: pair[0]
    )

    return [
        item
        for _, item in merged
    ]


def detect_evidence_conflicts(
    items: list[Evidence],
) -> list[dict]:
    """
    Detect materially different same-named structured records
    represented in the active evidence packet.
    """

    family_conflicts = {}
    for item in items:
        if item.origin == "primary" and item.evidence_family_id and item.conflict_status == "conflicted":
            family_conflicts[item.evidence_family_id] = {
                "content_type": item.content_type or "field",
                "name": item.record_name or item.heading,
                "source_ids": [],
                "authorities": [item.authority_id or "wotc:srd-5.2.1"],
                "evidence_family_id": item.evidence_family_id,
            }
    if family_conflicts:
        c = connect()
        try:
            for family_id, conflict in family_conflicts.items():
                conflict["source_ids"] = [row[0] for row in c.execute(
                    """SELECT DISTINCT ec.source_id FROM evidence_family_members m
                       JOIN evidence_chunks ec ON ec.id=m.evidence_chunk_id
                       WHERE m.family_id=? ORDER BY ec.source_id""", (family_id,)
                )]
        finally:
            c.close()
        return list(family_conflicts.values())

    structured = [
        item
        for item in items
        if (
            item.origin == "primary"
            and not item.evidence_family_id
            and item.content_type
            and item.record_name
        )
    ]

    primary_ids = [
        item.evidence_id
        for item in structured
    ]

    if len(primary_ids) < 2:
        return []

    c = connect()

    try:
        placeholders = ",".join(
            "?"
            for _ in primary_ids
        )

        sql = (
            "SELECT "
            "ec.evidence_id,"
            "cr.content_type,"
            "cr.name,"
            "cr.structured_json,"
            "s.id AS source_id,"
            "s.authority_type,"
            "s.priority "
            "FROM evidence_chunks ec "
            "JOIN content_records cr "
            "ON cr.id = ec.content_record_id "
            "JOIN sources s "
            "ON s.id = ec.source_id "
            f"WHERE ec.evidence_id IN ({placeholders}) "
            "AND s.enabled = 1 "
            "AND s.approved = 1 "
            "AND s.license_status = 'present' "
            "AND ("
            "s.edition IS NULL "
            "OR s.edition = ?"
            ")"
        )

        rows = c.execute(
            sql,
            (
                *primary_ids,
                settings.active_edition,
            ),
        ).fetchall()

        groups = {}

        for row in rows:
            if (
                not row["name"]
                or not row["content_type"]
            ):
                continue

            key = (
                row[
                    "content_type"
                ].lower(),
                row[
                    "name"
                ].strip().lower(),
            )

            groups.setdefault(
                key,
                [],
            ).append(row)

        conflicts = []

        for (
            content_type,
            name,
        ), group in groups.items():

            sources = {
                row["source_id"]
                for row in group
            }

            digests = {
                hashlib.sha256(
                    (
                        row[
                            "structured_json"
                        ]
                        or ""
                    ).encode(
                        "utf-8"
                    )
                ).hexdigest()
                for row in group
            }

            if (
                len(sources) > 1
                and len(digests) > 1
            ):
                conflicts.append(
                    {
                        "content_type": (
                            content_type
                        ),
                        "name": name,
                        "source_ids": sorted(
                            sources
                        ),
                        "authorities": sorted(
                            {
                                row[
                                    "authority_type"
                                ]
                                for row
                                in group
                            }
                        ),
                    }
                )

        return conflicts

    finally:
        c.close()


def diagnose(
    query: str,
    top_k: int | None = None,
) -> dict:
    plan = build_query_plan(
        query
    )

    items = search(
        query,
        top_k,
        expand_neighbors=True,
    )

    return {
        "query": query,
        "plan": plan.to_dict(),
        "results": [
            item.to_dict()
            for item in items
        ],
        "primary_count": sum(
            1
            for item in items
            if item.origin == "primary"
        ),
        "context_count": sum(
            1
            for item in items
            if item.origin == "context"
        ),
    }


def evidence_packet(
    items: list[Evidence],
) -> str:
    parts = []

    for evidence in items:
        role = (
            "PRIMARY HIT"
            if evidence.origin
            == "primary"
            else "ADJACENT CONTEXT"
        )

        if (
            evidence.page_pdf
            is not None
        ):
            location = (
                f"PDF page "
                f"{evidence.page_pdf}"
            )
        else:
            location = (
                "record "
                + (
                    evidence.page_label
                    or evidence.evidence_id
                )
            )

        parts.append(
            f"[{evidence.evidence_id}] "
            f"source={evidence.source_id} "
            f"authority_id={evidence.authority_id or '-'} "
            f"representation_id={evidence.representation_id or '-'} "
            f"authority="
            f"{evidence.authority_type} "
            f"edition="
            f"{evidence.edition or '-'} "
            f"| {location} "
            f"| {evidence.heading} "
            f"| {role}\n"
            f"{evidence.text}"
        )

    return (
        "\n\n---\n\n".join(
            parts
        )
    )
