from __future__ import annotations

import hashlib
import re

from dataclasses import asdict, dataclass, field

from .concepts import ALIASES, CONCEPTS
from .config import settings
from .db import connect
from .source import get_source_manifest, verify_source


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

    def to_dict(self):
        return asdict(self)


@dataclass
class QueryPlan:
    original: str
    terms: list[str]
    concepts: list[str]
    aliases: list[str]
    subqueries: list[str]

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
    )


def _escape(term: str) -> str:
    return term.replace(
        '"',
        '""',
    )


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
          s.edition,
          s.priority,
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
      ORDER BY rank
      LIMIT ?
    """

    return c.execute(
        sql,
        tuple(params),
    ).fetchall()


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

    # Source priority remains a modest relevance tie-breaker,
    # not the mechanism that enforces authority representation.
    score += (
        max(
            0.0,
            float(row["priority"]) - 70.0,
        )
        / 20.0
    )

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


def _verify_index(c):
    meta = dict(
        c.execute(
            """
            SELECT key, value
            FROM metadata
            """
        ).fetchall()
    )

    manifest = get_source_manifest(
        settings.source_id
    )

    expected = manifest.sha256

    if (
        meta.get("source_sha256")
        != expected
        or meta.get("source_id")
        != manifest.id
    ):
        raise RuntimeError(
            "SRD index does not match the approved source. "
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
        candidates[row["id"]] = (
            row,
            _score_row(
                row,
                plan,
                "broad",
            ),
            ["broad"],
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

            old = candidates.get(
                row["id"]
            )

            if old:
                candidates[
                    row["id"]
                ] = (
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
                candidates[
                    row["id"]
                ] = (
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
    )


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

        selected = (
            _merge_authority_candidates(
                official_ranked,
                supplemental_ranked,
                plan,
                final_k,
            )
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

            primary_ids.append(
                row["id"]
            )

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
                        s.edition,
                        s.priority
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

    structured = [
        item
        for item in items
        if (
            item.origin == "primary"
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
