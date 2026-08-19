import archie.answer as answer
from archie.retrieve import Evidence


def _evidence():
    return [
        Evidence(
            "E1", 184, "184", "Invisible",
            "Attack rolls against you have Disadvantage. If a creature can somehow see you, you don't gain this benefit against that creature.",
            1.0,
        )
    ]


def _audit_ok(claim_count=1):
    return {
        "premises":[{"index":0,"classification_valid":True,"reason":"forced unresolved"}],
        "premise_coverage_complete":True,
        "claims":[{"index":i,"supported":True,"reason":"supported"} for i in range(claim_count)],
        "answer_units":[{"index":0,"text":"supported rule","supporting_claim_indexes":list(range(claim_count)),"supported":True,"reason":"covered"}] if claim_count else [],
        "all_supported":True,
        "answer_fully_covered":True,
        "coverage_reason":"covered",
    }


def test_invisible_targeting_is_forced_unresolved():
    p=answer.forced_unresolved_premise("If I am Invisible, nobody can ever target me, right?")
    assert p == "Invisible creatures cannot ever be targeted"


def test_invisible_automatic_miss_is_forced_unresolved():
    p=answer.forced_unresolved_premise("If an Invisible creature can't be seen, attacks against it automatically miss, correct?")
    assert p == "Attacks against an Invisible creature automatically miss"


def test_prone_permission_inference_is_forced_unresolved():
    p=answer.forced_unresolved_premise("If Prone gives me Disadvantage with a bow, that means I am definitely allowed to fire one while Prone, right?")
    assert p == "Being Prone definitely permits the stated bow attack"


def test_forced_unresolved_overrides_model_contradicted_targeting(monkeypatch):
    evidence=_evidence()
    monkeypatch.setattr(answer,"search",lambda q:evidence)
    responses=iter([
        {
            "status":"VERIFIED",
            "answer":"Invisible creatures can be targeted. Attack rolls against them have Disadvantage.",
            "premises":[{"text":"Nobody can target invisible creatures","state":"CONTRADICTED","evidence_ids":["E1"]}],
            "claims":[
                {"text":"Invisible creatures can be targeted","evidence_ids":["E1"],"kind":"DIRECT"},
                {"text":"Attack rolls against an Invisible creature have Disadvantage","evidence_ids":["E1"],"kind":"DIRECT"},
            ],
            "reason":"draft",
        },
        _audit_ok(1),
    ])
    monkeypatch.setattr(answer,"chat_json",lambda system,user:next(responses))
    result=answer.ask("If I am Invisible, nobody can ever target me, right?",strict_audit=True)
    assert result.status == "PARTIAL"
    assert result.premises == [{"text":"Invisible creatures cannot ever be targeted","state":"UNRESOLVED","evidence_ids":[]}]
    assert "can't verify this premise" in result.answer
    assert "can be targeted" not in result.answer
    assert len(result.claims)==1
    assert "Disadvantage" in result.claims[0]["text"]


def test_forced_unresolved_overrides_invalid_model_status(monkeypatch):
    evidence=_evidence()
    monkeypatch.setattr(answer,"search",lambda q:evidence)
    responses=iter([
        {
            "status":"CONTRADICTED",
            "answer":"Attacks automatically miss.",
            "premises":[],
            "claims":[{"text":"Attack rolls against an Invisible creature have Disadvantage","evidence_ids":["E1"],"kind":"DIRECT"}],
            "reason":"draft",
        },
        _audit_ok(1),
    ])
    monkeypatch.setattr(answer,"chat_json",lambda system,user:next(responses))
    result=answer.ask("If an Invisible creature can't be seen, attacks against it automatically miss, correct?",strict_audit=True)
    assert result.status == "PARTIAL"
    assert "can't verify this premise" in result.answer
    assert "automatically miss" in result.premises[0]["text"]
    assert "Attack rolls against an Invisible creature have Disadvantage" in result.answer


def test_specific_attack_claim_does_not_settle_targetability():
    assert answer._claim_settles_forced_premise(
        "Attack rolls against an Invisible creature have Disadvantage",
        "Invisible creatures cannot ever be targeted",
    ) is False
    assert answer._claim_settles_forced_premise(
        "Invisible creatures can be targeted",
        "Invisible creatures cannot ever be targeted",
    ) is True
