import archie.answer as answer
from archie.llm import LLMContractError
from archie.retrieve import Evidence


def _evidence():
    return [Evidence("E1", 1, "1", "Test", "Rule text.", 1.0)]


def _answer_obj():
    return {
        "status": "VERIFIED",
        "answer": "Rule text.",
        "premises": [],
        "claims": [{"text": "Rule text.", "evidence_ids": ["E1"], "kind": "DIRECT"}],
        "reason": "E1",
    }


def _audit_ok():
    return {
        "premises": [],
        "premise_coverage_complete": True,
        "claims": [{"index": 0, "supported": True, "reason": "supported"}],
        "answer_units": [{
            "index": 0,
            "text": "Rule text.",
            "supporting_claim_indexes": [0],
            "supported": True,
            "reason": "covered",
        }],
        "all_supported": True,
        "answer_fully_covered": True,
        "coverage_reason": "covered",
    }


def test_direct_prone_longbow_permission_is_forced_unresolved():
    assert answer.forced_unresolved_premise("Can I use a longbow while I am Prone?") == \
        "Being Prone permits the stated bow attack"
    assert answer.forced_unresolved_premise("Am I allowed to fire a bow while Prone?") == \
        "Being Prone permits the stated bow attack"
    assert answer.forced_unresolved_premise("While Prone, can I use a longbow?") == \
        "Being Prone permits the stated bow attack"


def test_directly_answerable_permission_questions_are_not_globally_guarded():
    assert answer.forced_unresolved_premise("Can I move before and after my action?") is None
    assert answer.forced_unresolved_premise(
        "Can I reroll both dice when I have Advantage and use Heroic Inspiration?"
    ) is None


def test_prone_longbow_direct_question_renders_unresolved(monkeypatch):
    evidence = [Evidence(
        "E1", 186, "186", "Prone",
        "While you have the Prone condition, you have Disadvantage on attack rolls.",
        1.0,
    )]
    monkeypatch.setattr(answer, "search", lambda q: evidence)
    responses = iter([
        {
            "status": "VERIFIED",
            "answer": "Yes, you can use a longbow while Prone, but you have Disadvantage.",
            "premises": [],
            "claims": [
                {"text": "You can use a longbow while Prone", "evidence_ids": ["E1"], "kind": "DIRECT"},
                {"text": "While Prone, you have Disadvantage on attack rolls", "evidence_ids": ["E1"], "kind": "DIRECT"},
            ],
            "reason": "draft",
        },
        {
            "premises": [{"index": 0, "classification_valid": True, "reason": "unresolved"}],
            "premise_coverage_complete": True,
            "claims": [{"index": 0, "supported": True, "reason": "supported"}],
            "answer_units": [{"index": 0, "text": "Disadvantage rule", "supporting_claim_indexes": [0], "supported": True, "reason": "covered"}],
            "all_supported": True,
            "answer_fully_covered": True,
            "coverage_reason": "covered",
        },
    ])
    monkeypatch.setattr(answer, "chat_json", lambda system, user: next(responses))
    result = answer.ask("Can I use a longbow while I am Prone?", strict_audit=True)
    assert result.status == "PARTIAL"
    assert result.premises == [{
        "text": "Being Prone permits the stated bow attack",
        "state": "UNRESOLVED",
        "evidence_ids": [],
    }]
    assert "can't verify this premise" in result.answer
    assert "you can use a longbow" not in result.answer.lower()
    assert len(result.claims) == 1
    assert "Disadvantage" in result.claims[0]["text"]


def test_malformed_auditor_gets_one_correction_retry(monkeypatch):
    evidence = _evidence()
    monkeypatch.setattr(answer, "search", lambda q: evidence)
    calls = {"n": 0}

    def fake_chat(system, user):
        calls["n"] += 1
        if calls["n"] == 1:
            return _answer_obj()
        if calls["n"] == 2:
            raise LLMContractError("Model did not return valid JSON.")
        if calls["n"] == 3:
            assert "AUDIT FORMAT CORRECTION RETRY" in user
            return _audit_ok()
        raise AssertionError("unexpected extra model call")

    monkeypatch.setattr(answer, "chat_json", fake_chat)
    result = answer.ask("test", strict_audit=True)
    assert result.status == "VERIFIED"
    assert calls["n"] == 3


def test_repeated_malformed_auditor_still_fails_closed(monkeypatch):
    evidence = _evidence()
    monkeypatch.setattr(answer, "search", lambda q: evidence)
    calls = {"n": 0}

    def fake_chat(system, user):
        calls["n"] += 1
        if calls["n"] == 1:
            return _answer_obj()
        raise LLMContractError("Model did not return valid JSON.")

    monkeypatch.setattr(answer, "chat_json", fake_chat)
    result = answer.ask("test", strict_audit=True)
    assert result.status == "PARTIAL"
    assert "malformed JSON" in result.reason
    assert calls["n"] == 3
