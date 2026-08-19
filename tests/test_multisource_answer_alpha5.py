from __future__ import annotations

import archie.answer as ans
import archie.retrieve as retrieve

from archie.provenance import source_usage
from archie.retrieve import (
    Evidence,
    QueryPlan,
)


def _ev(
    evidence_id: str,
    source_id: str,
    authority: str,
    text: str,
    score: float = 10.0,
) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        page_pdf=(
            10
            if authority
            == "official_srd"
            else None
        ),
        page_label=None,
        heading="Test Rule",
        text=text,
        score=score,
        source_id=source_id,
        authority_type=authority,
        edition="2024",
        origin="primary",
        matched_by=["test"],
        content_type="spells",
        record_name="Mystic Spark",
        source_priority=(
            100
            if authority
            == "official_srd"
            else 80
        ),
    )


def _candidate(
    row_id: int,
    evidence_id: str,
    authority: str,
    score: float,
    *,
    matched_by=None,
):
    if matched_by is None:
        matched_by = ["broad"]

    priority = (
        100
        if authority
        == "official_srd"
        else 80
    )

    source_id = (
        "srd521"
        if authority
        == "official_srd"
        else "open5e:srd-2024"
    )

    row = {
        "id": row_id,
        "evidence_id": evidence_id,
        "source_id": source_id,
        "page_pdf": (
            row_id
            if authority
            == "official_srd"
            else None
        ),
        "page_label": None,
        "heading": "Test Rule",
        "text": evidence_id,
        "content_record_id": None,
        "content_type": None,
        "record_name": None,
        "authority_type": authority,
        "edition": "2024",
        "priority": priority,
        "rank": -score,
    }

    return (
        row,
        score,
        matched_by,
    )


def test_supplemental_only_answer_is_allowed_and_labeled(
    monkeypatch,
):
    evidence = [
        _ev(
            "O5E-1",
            "open5e:srd-2024",
            "approved_supplement",
            "Mystic Spark deals test damage.",
        )
    ]

    monkeypatch.setattr(
        ans,
        "search",
        lambda q: evidence,
    )

    monkeypatch.setattr(
        ans,
        "detect_evidence_conflicts",
        lambda items: [],
    )

    monkeypatch.setattr(
        ans,
        "chat_json",
        lambda system, user: {
            "status": "VERIFIED",
            "answer": (
                "Mystic Spark deals "
                "test damage."
            ),
            "claims": [
                {
                    "text": (
                        "Mystic Spark deals "
                        "test damage."
                    ),
                    "evidence_ids": [
                        "O5E-1"
                    ],
                    "kind": "DIRECT",
                }
            ],
            "premises": [],
            "reason": (
                "Grounded in approved "
                "supplemental evidence."
            ),
        },
    )

    result = ans.ask(
        "What does Mystic Spark do?",
        strict_audit=False,
    )

    assert result.status == "VERIFIED"

    assert (
        result.source_mode
        == "supplemental_only"
    )

    assert [
        item["source_id"]
        for item
        in result.sources_used
    ] == [
        "open5e:srd-2024"
    ]

    assert (
        "Authority mode: "
        "supplemental_only."
        in result.reason
    )


def test_mixed_answer_reports_only_cited_sources_and_orders_official_first(
    monkeypatch,
):
    evidence = [
        _ev(
            "SRD-1",
            "srd521",
            "official_srd",
            "Official test fact.",
            12,
        ),
        _ev(
            "O5E-1",
            "open5e:srd-2024",
            "approved_supplement",
            "Supplemental test fact.",
            10,
        ),
        _ev(
            "O5E-UNUSED",
            "open5e:srd-2024",
            "approved_supplement",
            "Unused retrieved fact.",
            9,
        ),
    ]

    monkeypatch.setattr(
        ans,
        "search",
        lambda q: evidence,
    )

    monkeypatch.setattr(
        ans,
        "detect_evidence_conflicts",
        lambda items: [],
    )

    monkeypatch.setattr(
        ans,
        "chat_json",
        lambda system, user: {
            "status": "VERIFIED",
            "answer": (
                "Official test fact. "
                "Supplemental test fact."
            ),
            "claims": [
                {
                    "text": (
                        "Official test fact."
                    ),
                    "evidence_ids": [
                        "SRD-1"
                    ],
                    "kind": "DIRECT",
                },
                {
                    "text": (
                        "Supplemental test fact."
                    ),
                    "evidence_ids": [
                        "O5E-1"
                    ],
                    "kind": "DIRECT",
                },
            ],
            "premises": [],
            "reason": "Grounded.",
        },
    )

    result = ans.ask(
        "Give me the two test facts.",
        strict_audit=False,
    )

    assert (
        result.source_mode
        == "mixed"
    )

    assert [
        item["source_id"]
        for item
        in result.sources_used
    ] == [
        "srd521",
        "open5e:srd-2024",
    ]

    assert (
        "O5E-UNUSED"
        not in {
            evidence_id
            for item
            in result.sources_used
            for evidence_id
            in item["evidence_ids"]
        }
    )


def test_source_conflict_fails_closed_before_llm(
    monkeypatch,
):
    evidence = [
        _ev(
            "A",
            "source-a",
            "official_srd",
            "Version A.",
        ),
        _ev(
            "B",
            "source-b",
            "approved_supplement",
            "Version B.",
        ),
    ]

    monkeypatch.setattr(
        ans,
        "search",
        lambda q: evidence,
    )

    monkeypatch.setattr(
        ans,
        "detect_evidence_conflicts",
        lambda items: [
            {
                "content_type": "spells",
                "name": "mystic spark",
                "source_ids": [
                    "source-a",
                    "source-b",
                ],
                "authorities": [
                    "approved_supplement",
                    "official_srd",
                ],
            }
        ],
    )

    def should_not_run(
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "LLM must not run for "
            "deterministic source conflict"
        )

    monkeypatch.setattr(
        ans,
        "chat_json",
        should_not_run,
    )

    result = ans.ask(
        "What does Mystic Spark do?",
        strict_audit=False,
    )

    assert result.status == "PARTIAL"

    assert (
        "conflicting approved "
        "source records"
        in result.answer
    )

    assert (
        "Fail-closed source conflict"
        in result.reason
    )


def test_exact_duplicate_evidence_is_suppressed_with_official_item_kept():
    official = _ev(
        "SRD-1",
        "srd521",
        "official_srd",
        "Same exact fact.",
        10,
    )

    # Deliberately give the supplemental copy a higher score.
    # Exact duplicate suppression must still retain official
    # evidence.
    supplement = _ev(
        "O5E-1",
        "open5e:srd-2024",
        "approved_supplement",
        "Same   exact\n fact.",
        50,
    )

    deduped = (
        retrieve
        ._dedupe_exact_evidence(
            [
                supplement,
                official,
            ]
        )
    )

    assert [
        item.evidence_id
        for item in deduped
    ] == [
        "SRD-1"
    ]


def test_source_usage_ignores_retrieved_but_uncited_sources():
    official = _ev(
        "SRD-1",
        "srd521",
        "official_srd",
        "Official fact.",
    )

    supplement = _ev(
        "O5E-1",
        "open5e:srd-2024",
        "approved_supplement",
        "Supplemental fact.",
    )

    mode, uses = source_usage(
        [
            official,
            supplement,
        ],
        [
            {
                "evidence_ids": [
                    "O5E-1"
                ]
            }
        ],
    )

    assert (
        mode
        == "supplemental_only"
    )

    assert [
        item.source_id
        for item in uses
    ] == [
        "open5e:srd-2024"
    ]


def test_authority_merge_reserves_official_evidence():
    """
    Supplemental evidence may rank very highly, but enabling it
    must not consume the complete primary evidence window.
    """

    plan = QueryPlan(
        original="test",
        terms=["test"],
        concepts=[],
        aliases=[],
        subqueries=[],
    )

    official = [
        _candidate(
            i,
            f"SRD-{i}",
            "official_srd",
            10 - i,
        )
        for i in range(
            1,
            11,
        )
    ]

    supplemental = [
        _candidate(
            100 + i,
            f"O5E-{i}",
            "approved_supplement",
            100 - i,
        )
        for i in range(
            1,
            11,
        )
    ]

    selected = (
        retrieve
        ._merge_authority_candidates(
            official,
            supplemental,
            plan,
            12,
        )
    )

    authorities = [
        item[0][
            "authority_type"
        ]
        for item in selected
    ]

    assert (
        authorities.count(
            "official_srd"
        )
        >= 8
    )

    assert (
        authorities.count(
            "approved_supplement"
        )
        >= 1
    )


def test_authority_merge_preserves_exact_concept_hits_from_official_pool():
    """
    Exact concept anchors from the official source must survive
    even when supplemental candidates have much higher raw
    relevance scores.
    """

    plan = QueryPlan(
        original=(
            "What is the difference "
            "between an ability check "
            "and a saving throw?"
        ),
        terms=[
            "ability",
            "check",
            "saving",
            "throw",
        ],
        concepts=[
            "ability check",
            "saving throw",
        ],
        aliases=[],
        subqueries=[
            "ability check",
            "saving throw",
        ],
    )

    official = [
        _candidate(
            1,
            "SRD-ABILITY",
            "official_srd",
            12,
            matched_by=[
                "exact:ability check"
            ],
        ),
        _candidate(
            2,
            "SRD-SAVE",
            "official_srd",
            11,
            matched_by=[
                "exact:saving throw"
            ],
        ),
        _candidate(
            3,
            "SRD-OTHER",
            "official_srd",
            30,
        ),
    ]

    supplemental = [
        _candidate(
            101 + i,
            f"O5E-{i}",
            "approved_supplement",
            100 - i,
        )
        for i in range(
            8
        )
    ]

    selected = (
        retrieve
        ._merge_authority_candidates(
            official,
            supplemental,
            plan,
            6,
        )
    )

    ids = {
        item[0]["evidence_id"]
        for item in selected
    }

    assert "SRD-ABILITY" in ids
    assert "SRD-SAVE" in ids


def test_supplemental_only_pool_can_use_full_budget():
    """
    Official reservation must not waste slots when there is no
    relevant official evidence.
    """

    plan = QueryPlan(
        original=(
            "What does Mystic Spark do?"
        ),
        terms=[
            "mystic",
            "spark",
        ],
        concepts=[],
        aliases=[],
        subqueries=[],
    )

    supplemental = [
        _candidate(
            100 + i,
            f"O5E-{i}",
            "approved_supplement",
            20 - i,
        )
        for i in range(
            10
        )
    ]

    selected = (
        retrieve
        ._merge_authority_candidates(
            [],
            supplemental,
            plan,
            8,
        )
    )

    assert len(selected) == 8

    assert all(
        item[0][
            "authority_type"
        ]
        == "approved_supplement"
        for item in selected
    )
