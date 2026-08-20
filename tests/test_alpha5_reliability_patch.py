from __future__ import annotations

import sqlite3

import pytest

import archie.answer as answer_module

from archie.config import settings
from archie.ingest import ingest
from archie.llm import LLMContractError, parse_json
from archie.retrieve import search


def test_parse_json_accepts_clean_object():
    obj = parse_json('{"ok":true,"claims":[]}')

    assert obj == {
        "ok": True,
        "claims": [],
    }


def test_parse_json_accepts_json_code_fence():
    obj = parse_json(
        '```json\n'
        '{"ok":true}\n'
        '```'
    )

    assert obj == {
        "ok": True,
    }


def test_parse_json_extracts_first_valid_object_from_noise():
    obj = parse_json(
        'model preamble\n'
        '{"ok":true,"value":7}\n'
        'model epilogue'
    )

    assert obj == {
        "ok": True,
        "value": 7,
    }


def test_parse_json_rejects_truncated_object():
    with pytest.raises(LLMContractError):
        parse_json('{"ok":true,"claims":[')


def test_forced_prone_permission_question_remains_neutral():
    premise = answer_module.forced_unresolved_premise(
        "Can I use a longbow while I am Prone?"
    )

    assert premise == (
        "Being Prone permits the stated bow attack"
    )


def test_unresolved_answer_does_not_imply_permission_or_prohibition():
    rendered = answer_module._render_unresolved_answer(
        [
            {
                "text": (
                    "Being Prone permits the stated bow attack"
                ),
                "state": "UNRESOLVED",
                "evidence_ids": [],
            }
        ],
        [
            {
                "text": (
                    "While you have the Prone condition, "
                    "you have Disadvantage on attack rolls."
                ),
                "evidence_ids": [
                    "SRD521-P186-C02"
                ],
                "kind": "DIRECT",
            }
        ],
    )

    lower = rendered.lower()

    assert "can't verify this premise" in lower
    assert "disadvantage" in lower
    assert "you can use" not in lower
    assert "you cannot use" not in lower


def test_persistent_metadata_tamper_still_fails_closed():
    ingest()

    c = sqlite3.connect(settings.database)

    try:
        c.execute(
            """
            UPDATE metadata
            SET value = ?
            WHERE key = 'source_sha256'
            """,
            ("0" * 64,),
        )
        c.commit()
    finally:
        c.close()

    with pytest.raises(
        RuntimeError,
        match="SRD index does not match the approved source",
    ):
        search("What does Heroic Inspiration do?")

    # Restore generated storage so following tests begin clean.
    ingest()


def test_repeated_sequential_searches_keep_index_identity_stable():
    ingest()

    questions = [
        "What happens when I have advantage on a roll?",
        "What does the Prone condition do?",
        "How does Concentration work?",
        "What does Heroic Inspiration do?",
        "What is Armor Class?",
    ]

    for _ in range(3):
        for question in questions:
            hits = search(question)
            assert hits

    c = sqlite3.connect(settings.database)

    try:
        rows = dict(
            c.execute(
                """
                SELECT key, value
                FROM metadata
                WHERE key IN (
                    'source_id',
                    'source_sha256'
                )
                """
            ).fetchall()
        )
    finally:
        c.close()

    assert rows["source_id"] == settings.source_id

    from archie.source import get_source_manifest

    manifest = get_source_manifest(settings.source_id)

    assert rows["source_sha256"] == manifest.sha256


def test_auditor_uses_dedicated_output_budget(monkeypatch):
    seen = []

    def fake_chat_json(
        system,
        user,
        temperature=0.0,
        *,
        max_tokens=None,
    ):
        seen.append(max_tokens)

        return {
            "premises": [],
            "premise_coverage_complete": True,
            "claims": [
                {
                    "index": 0,
                    "supported": True,
                    "reason": "supported",
                }
            ],
            "answer_units": [
                {
                    "index": 0,
                    "text": "test",
                    "supporting_claim_indexes": [0],
                    "supported": True,
                    "reason": "supported",
                }
            ],
            "all_supported": True,
            "answer_fully_covered": True,
            "coverage_reason": "covered",
        }

    monkeypatch.setattr(
        answer_module,
        "chat_json",
        fake_chat_json,
    )

    audit, error, repaired = answer_module._audit_answer(
        "test audit",
        claim_count=1,
        premise_count=0,
    )

    assert error is None
    assert repaired is False
    assert audit is not None

    assert seen == [
        settings.llm_audit_max_tokens
    ]

    assert (
        settings.llm_audit_max_tokens
        > settings.llm_max_tokens
    )


def test_semantic_audit_rejection_gets_one_evidence_correction_retry(
    monkeypatch,
):
    from archie.retrieve import Evidence

    evidence = [
        Evidence(
            "E1",
            177,
            "177",
            "Rules Glossary",
            (
                "An Armor Class (AC) is the target number "
                "for an attack roll. AC represents how "
                "difficult it is to hit a target."
            ),
            10.0,
        ),
        Evidence(
            "E2",
            177,
            "177",
            "Rules Glossary",
            (
                "An attack roll is a D20 Test that "
                "represents making an attack."
            ),
            9.0,
        ),
    ]

    monkeypatch.setattr(
        answer_module,
        "search",
        lambda q: evidence,
    )

    calls = {
        "n": 0,
    }

    def fake_chat(
        system,
        user,
    ):
        calls["n"] += 1

        # Initial answer: correct fact, wrong evidence binding.
        if calls["n"] == 1:
            return {
                "status": "VERIFIED",
                "answer": (
                    "Your Armor Class is the target number "
                    "for an attack roll."
                ),
                "premises": [],
                "claims": [
                    {
                        "text": (
                            "Armor Class is the target number "
                            "for an attack roll."
                        ),
                        "evidence_ids": [
                            "E2"
                        ],
                        "kind": "DIRECT",
                    }
                ],
                "reason": "draft",
            }

        # First audit: valid JSON, but semantic rejection.
        if calls["n"] == 2:
            return {
                "premises": [],
                "premise_coverage_complete": True,
                "claims": [
                    {
                        "index": 0,
                        "supported": False,
                        "reason": (
                            "E2 does not define Armor Class "
                            "as the target number."
                        ),
                    }
                ],
                "answer_units": [
                    {
                        "index": 0,
                        "text": (
                            "Armor Class is the target number "
                            "for an attack roll."
                        ),
                        "supporting_claim_indexes": [
                            0
                        ],
                        "supported": False,
                        "reason": (
                            "The cited claim is not supported "
                            "by E2."
                        ),
                    }
                ],
                "all_supported": False,
                "answer_fully_covered": False,
                "coverage_reason": (
                    "Wrong evidence entry cited."
                ),
            }

        # Bounded correction: same answer, precise evidence ID.
        if calls["n"] == 3:
            assert (
                "EVIDENCE-CITATION CORRECTION RETRY"
                in user
            )

            assert (
                "AUDITOR FEEDBACK"
                in user
            )

            return {
                "status": "VERIFIED",
                "answer": (
                    "Your Armor Class is the target number "
                    "for an attack roll."
                ),
                "premises": [],
                "claims": [
                    {
                        "text": (
                            "Armor Class is the target number "
                            "for an attack roll."
                        ),
                        "evidence_ids": [
                            "E1"
                        ],
                        "kind": "DIRECT",
                    }
                ],
                "reason": "corrected",
            }

        # Second audit succeeds.
        if calls["n"] == 4:
            return {
                "premises": [],
                "premise_coverage_complete": True,
                "claims": [
                    {
                        "index": 0,
                        "supported": True,
                        "reason": (
                            "E1 directly establishes the claim."
                        ),
                    }
                ],
                "answer_units": [
                    {
                        "index": 0,
                        "text": (
                            "Armor Class is the target number "
                            "for an attack roll."
                        ),
                        "supporting_claim_indexes": [
                            0
                        ],
                        "supported": True,
                        "reason": "covered",
                    }
                ],
                "all_supported": True,
                "answer_fully_covered": True,
                "coverage_reason": "covered",
            }

        raise AssertionError(
            "Unexpected extra model call"
        )

    monkeypatch.setattr(
        answer_module,
        "chat_json",
        fake_chat,
    )

    result = answer_module.ask(
        "Why is my armor number important?",
        strict_audit=True,
    )

    assert result.status == "VERIFIED"

    assert calls["n"] == 4

    assert result.claims[0][
        "evidence_ids"
    ] == [
        "E1"
    ]

    assert (
        "Evidence-citation correction retry succeeded."
        in result.reason
    )


def test_failed_evidence_correction_retry_still_fails_closed(
    monkeypatch,
):
    from archie.retrieve import Evidence

    evidence = [
        Evidence(
            "E1",
            177,
            "177",
            "Rules Glossary",
            "Directly supported rule.",
            10.0,
        ),
        Evidence(
            "E2",
            177,
            "177",
            "Rules Glossary",
            "Related but insufficient rule.",
            9.0,
        ),
    ]

    monkeypatch.setattr(
        answer_module,
        "search",
        lambda q: evidence,
    )

    calls = {
        "n": 0,
    }

    def rejected_audit():
        return {
            "premises": [],
            "premise_coverage_complete": True,
            "claims": [
                {
                    "index": 0,
                    "supported": False,
                    "reason": "wrong citation",
                }
            ],
            "answer_units": [
                {
                    "index": 0,
                    "text": "Claim.",
                    "supporting_claim_indexes": [
                        0
                    ],
                    "supported": False,
                    "reason": "wrong citation",
                }
            ],
            "all_supported": False,
            "answer_fully_covered": False,
            "coverage_reason": "wrong citation",
        }

    def fake_chat(
        system,
        user,
    ):
        calls["n"] += 1

        if calls["n"] in {
            1,
            3,
        }:
            return {
                "status": "VERIFIED",
                "answer": "Claim.",
                "premises": [],
                "claims": [
                    {
                        "text": "Claim.",
                        "evidence_ids": [
                            "E2"
                        ],
                        "kind": "DIRECT",
                    }
                ],
                "reason": "draft",
            }

        if calls["n"] in {
            2,
            4,
        }:
            return rejected_audit()

        raise AssertionError(
            "Unexpected extra model call"
        )

    monkeypatch.setattr(
        answer_module,
        "chat_json",
        fake_chat,
    )

    result = answer_module.ask(
        "test",
        strict_audit=True,
    )

    assert result.status == "PARTIAL"

    assert calls["n"] == 4

    assert (
        "correction retry also failed audit"
        in result.reason
    )
