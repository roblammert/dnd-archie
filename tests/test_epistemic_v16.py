import pytest
import archie.answer as answer
from archie.retrieve import Evidence


def _evidence(text="Rule evidence."):
    return [Evidence("E1", 1, "1", "Test", text, 1.0)]


def _base(claims=None, premises=None, status="VERIFIED", answer_text="Rule text."):
    return {
        "status": status,
        "answer": answer_text,
        "premises": premises or [],
        "claims": claims if claims is not None else [
            {"text": "Rule text.", "evidence_ids": ["E1"], "kind": "DIRECT"}
        ],
        "reason": "grounded",
    }


def _good_audit(claim_count=1, premise_count=0, answer_units=True):
    return {
        "premises":[{"index":i,"classification_valid":True,"reason":"valid"} for i in range(premise_count)],
        "premise_coverage_complete":True,
        "claims":[{"index":i,"supported":True,"reason":"supported"} for i in range(claim_count)],
        "answer_units":([{"index":0,"text":"Rule text.","supporting_claim_indexes":list(range(claim_count)),"supported":True,"reason":"covered"}] if answer_units else []),
        "all_supported":True,
        "answer_fully_covered":True,
        "coverage_reason":"covered",
    }


def test_supported_premise_requires_evidence():
    obj=_base(premises=[{"text":"X is true","state":"SUPPORTED","evidence_ids":[]}])
    with pytest.raises(ValueError, match="requires evidence IDs"):
        answer._validate_shape(obj,{"E1"})


def test_contradicted_premise_requires_evidence():
    obj=_base(premises=[{"text":"X is true","state":"CONTRADICTED","evidence_ids":[]}])
    with pytest.raises(ValueError, match="requires evidence IDs"):
        answer._validate_shape(obj,{"E1"})


def test_unresolved_premise_must_not_claim_supporting_evidence():
    obj=_base(status="PARTIAL",premises=[{"text":"X is true","state":"UNRESOLVED","evidence_ids":["E1"]}])
    with pytest.raises(ValueError, match="must not claim evidentiary support"):
        answer._validate_shape(obj,{"E1"})


def test_unresolved_premise_cannot_be_verified():
    obj=_base(premises=[{"text":"X is true","state":"UNRESOLVED","evidence_ids":[]}])
    with pytest.raises(ValueError, match="cannot be VERIFIED or DERIVED"):
        answer._validate_shape(obj,{"E1"})


def test_premise_state_normalization():
    obj=answer._normalize_contract(_base(status="PARTIAL",premises=[{"text":"X","state":" unresolved ","evidence_ids":[]}]))
    assert obj["premises"][0]["state"] == "UNRESOLVED"


def test_auditor_rejection_of_bad_premise_fails_closed(monkeypatch):
    evidence=_evidence()
    monkeypatch.setattr(answer,"search",lambda q:evidence)
    responses=iter([
        _base(
            premises=[{"text":"Invisible creatures can never be targeted","state":"CONTRADICTED","evidence_ids":["E1"]}],
            answer_text="Invisible creatures can be targeted."
        ),
        {
            "premises":[{"index":0,"classification_valid":False,"reason":"Evidence about attacks does not settle targeting."}],
            "premise_coverage_complete":True,
            "claims":[{"index":0,"supported":True,"reason":"claim itself supported"}],
            "answer_units":[{"index":0,"text":"Invisible creatures can be targeted.","supporting_claim_indexes":[0],"supported":False,"reason":"targeting not established"}],
            "all_supported":False,
            "answer_fully_covered":False,
            "coverage_reason":"non-entailment"
        }
    ])
    monkeypatch.setattr(answer,"chat_json",lambda system,user:next(responses))
    result=answer.ask("If I am Invisible, nobody can ever target me, right?",strict_audit=True)
    assert result.status == "PARTIAL"
    assert "premise classifications rejected" in result.reason


def test_omitted_material_premise_fails_closed(monkeypatch):
    evidence=_evidence()
    monkeypatch.setattr(answer,"search",lambda q:evidence)
    responses=iter([
        _base(answer_text="Attack rolls have Disadvantage.", premises=[]),
        {
            "premises":[],
            "premise_coverage_complete":False,
            "claims":[{"index":0,"supported":True,"reason":"attack rule supported"}],
            "answer_units":[{"index":0,"text":"Attack rolls have Disadvantage.","supporting_claim_indexes":[0],"supported":True,"reason":"covered"}],
            "all_supported":True,
            "answer_fully_covered":True,
            "coverage_reason":"Answer claim covered but question premise omitted."
        }
    ])
    monkeypatch.setattr(answer,"chat_json",lambda system,user:next(responses))
    result=answer.ask("If I am Invisible, nobody can ever target me, right?",strict_audit=True)
    assert result.status == "PARTIAL"
    assert ("model contract" in result.reason.lower() or "fail-closed audit" in result.reason.lower())


def test_unresolved_premise_can_be_audited_without_rules_claims(monkeypatch):
    evidence=_evidence()
    monkeypatch.setattr(answer,"search",lambda q:evidence)
    responses=iter([
        _base(
            status="PARTIAL",
            answer_text="The supplied evidence does not establish whether X is true.",
            premises=[{"text":"X is true","state":"UNRESOLVED","evidence_ids":[]}],
            claims=[]
        ),
        {
            "premises":[{"index":0,"classification_valid":True,"reason":"Neither side established."}],
            "premise_coverage_complete":True,
            "claims":[],
            "answer_units":[],
            "all_supported":True,
            "answer_fully_covered":True,
            "coverage_reason":"Only epistemic uncertainty is stated."
        }
    ])
    monkeypatch.setattr(answer,"chat_json",lambda system,user:next(responses))
    result=answer.ask("X is true, right?",strict_audit=True)
    assert result.status == "NOT_IN_SRD"
    assert result.premises[0]["state"] == "UNRESOLVED"


def test_ordinary_question_keeps_empty_premises(monkeypatch):
    evidence=_evidence()
    monkeypatch.setattr(answer,"search",lambda q:evidence)
    responses=iter([_base(), _good_audit()])
    monkeypatch.setattr(answer,"chat_json",lambda system,user:next(responses))
    result=answer.ask("What does this rule do?",strict_audit=True)
    assert result.status == "VERIFIED"
    assert result.premises == []
