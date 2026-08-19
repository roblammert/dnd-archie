import archie.answer as answer
from archie.retrieve import Evidence


def _evidence():
    return [Evidence("E1", 1, "1", "Test", "Supported rule text.", 1.0)]


def test_direct_yes_no_question_is_not_premise_bearing():
    assert answer.premise_mode("Does Advantage stack if I get it from two different things?") == "NONE"
    assert answer.premise_mode("Can I reroll both dice when I have Advantage and use Heroic Inspiration?") == "NONE"


def test_character_calculation_inputs_are_not_premises():
    assert answer.premise_mode("If my Wisdom modifier is +3 and I am proficient in Perception with a +2 proficiency bonus, what is my Passive Perception?") == "NONE"


def test_explicit_assertion_cues_require_premise_classification():
    assert answer.premise_mode("Because two sources of Advantage let me roll three d20s, which one do I keep?") == "REQUIRED"
    assert answer.premise_mode("If I am Invisible, nobody can ever target me, right?") == "REQUIRED"
    assert answer.premise_mode("If the SRD doesn't mention this spell, does that mean the spell doesn't exist?") == "REQUIRED"
    assert answer.premise_mode("If an Invisible creature can't be seen, attacks against it automatically miss, correct?") == "REQUIRED"


def test_mode_none_rejects_model_invented_premise():
    try:
        answer._validate_premise_mode([{"text":"invented","state":"UNRESOLVED","evidence_ids":[]}], "NONE")
    except ValueError as exc:
        assert "must not contain premise" in str(exc)
    else:
        raise AssertionError("expected rejection")


def test_required_mode_rejects_omitted_premise():
    try:
        answer._validate_premise_mode([], "REQUIRED")
    except ValueError as exc:
        assert "requires a material premise" in str(exc)
    else:
        raise AssertionError("expected rejection")


def test_unresolved_answer_is_rendered_neutrally():
    text=answer._render_unresolved_answer(
        [{"text":"Invisible creatures can never be targeted","state":"UNRESOLVED","evidence_ids":[]}],
        [{"text":"Attack rolls against an Invisible creature have Disadvantage","evidence_ids":["E1"],"kind":"DIRECT"}],
    )
    assert "can't verify this premise" in text
    assert "does not prevent all targeting" not in text
    assert "Attack rolls against an Invisible creature have Disadvantage" in text


def test_unresolved_final_answer_is_canonicalized_after_successful_audit(monkeypatch):
    evidence=_evidence()
    monkeypatch.setattr(answer, "search", lambda q: evidence)
    responses=iter([
        {
            "status":"PARTIAL",
            "answer":"It does not prevent all targeting. Supported rule text.",
            "premises":[{"text":"Invisible creatures can never be targeted","state":"UNRESOLVED","evidence_ids":[]}],
            "claims":[{"text":"Supported rule text","evidence_ids":["E1"],"kind":"DIRECT"}],
            "reason":"draft",
        },
        {
            "premises":[{"index":0,"classification_valid":True,"reason":"unresolved"}],
            "premise_coverage_complete":True,
            "claims":[{"index":0,"supported":True,"reason":"supported"}],
            "answer_units":[{"index":0,"text":"Supported rule text.","supporting_claim_indexes":[0],"supported":True,"reason":"supported"}],
            "all_supported":True,
            "answer_fully_covered":True,
            "coverage_reason":"covered",
        },
    ])
    monkeypatch.setattr(answer, "chat_json", lambda system,user: next(responses))
    result=answer.ask("If I am Invisible, nobody can ever target me, right?", strict_audit=True)
    assert result.status == "PARTIAL"
    assert "can't verify this premise" in result.answer
    assert "does not prevent all targeting" not in result.answer


def test_absence_inference_guard_detects_non_entailment_questions():
    assert answer.absence_inference_guard("If the SRD doesn't mention this spell, does that mean the spell doesn't exist?") is True
    assert answer.absence_inference_guard("If the rules only describe natural 20s on attacks, that means natural 20s do nothing special on ability checks, right?") is True
    assert answer.absence_inference_guard("Does Advantage stack?") is False


def test_absence_guard_requires_unresolved_classification():
    try:
        answer._validate_premise_mode(
            [{"text":"Missing means nonexistent","state":"SUPPORTED","evidence_ids":["E1"]}],
            "REQUIRED",
            True,
        )
    except ValueError as exc:
        assert "must remain UNRESOLVED" in str(exc)
    else:
        raise AssertionError("expected absence inference rejection")
