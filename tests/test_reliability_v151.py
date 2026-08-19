import archie.answer as answer
from archie.retrieve import Evidence


def _evidence():
    return [Evidence("E1",1,"1","Test","Rule text.",1.0)]


def test_invalid_kind_is_safely_normalized(monkeypatch):
    evidence=_evidence()
    monkeypatch.setattr(answer,"search",lambda q:evidence)
    monkeypatch.setattr(answer,"chat_json",lambda system,user:{
        "status":"verified",
        "answer":"Rule text.",
        "claims":[{"text":"Rule text.","evidence_ids":["E1"],"kind":" direct "}],
        "reason":"E1"
    })
    result=answer.ask("test",strict_audit=False)
    assert result.status=="VERIFIED"
    assert result.claims[0]["kind"]=="DIRECT"


def test_missing_evidence_ids_gets_one_correction_retry(monkeypatch):
    evidence=_evidence()
    monkeypatch.setattr(answer,"search",lambda q:evidence)
    responses=iter([
        {
            "status":"VERIFIED","answer":"Rule text.",
            "claims":[{"text":"Rule text.","kind":"DIRECT"}],"reason":"bad"
        },
        {
            "status":"VERIFIED","answer":"Rule text.",
            "claims":[{"text":"Rule text.","evidence_ids":["E1"],"kind":"DIRECT"}],"reason":"E1"
        }
    ])
    monkeypatch.setattr(answer,"chat_json",lambda system,user:next(responses))
    result=answer.ask("test",strict_audit=False)
    assert result.status=="VERIFIED"
    assert result.claims[0]["evidence_ids"]==["E1"]


def test_repeated_bad_contract_fails_closed_not_cli_error(monkeypatch):
    evidence=_evidence()
    monkeypatch.setattr(answer,"search",lambda q:evidence)
    monkeypatch.setattr(answer,"chat_json",lambda system,user:{
        "status":"VERIFIED","answer":"Rule text.",
        "claims":[{"text":"Rule text.","kind":"FACT"}],"reason":"bad"
    })
    result=answer.ask("test",strict_audit=False)
    assert result.status=="PARTIAL"
    assert result.claims==[]
    assert "model contract" in result.reason.lower()


def test_audit_requires_every_answer_unit(monkeypatch):
    evidence=_evidence()
    monkeypatch.setattr(answer,"search",lambda q:evidence)
    responses=iter([
        {
            "status":"VERIFIED",
            "answer":"You may do X, but doing X has Disadvantage.",
            "claims":[{"text":"Doing X has Disadvantage.","evidence_ids":["E1"],"kind":"DIRECT"}],
            "reason":"E1"
        },
        {
            "claims":[{"index":0,"supported":True,"reason":"penalty supported"}],
            "answer_units":[
                {"index":0,"text":"You may do X","supporting_claim_indexes":[],"supported":False,"reason":"permission unsupported"},
                {"index":1,"text":"Doing X has Disadvantage","supporting_claim_indexes":[0],"supported":True,"reason":"supported"}
            ],
            "all_supported":True,
            "answer_fully_covered":False,
            "coverage_reason":"permission is not evidenced"
        }
    ])
    monkeypatch.setattr(answer,"chat_json",lambda system,user:next(responses))
    result=answer.ask("Can I do X?",strict_audit=True)
    assert result.status=="PARTIAL"
    assert "unsupported mechanics" in result.reason


def test_audit_missing_answer_units_fails_closed(monkeypatch):
    evidence=_evidence()
    monkeypatch.setattr(answer,"search",lambda q:evidence)
    responses=iter([
        {
            "status":"VERIFIED","answer":"Rule text.",
            "claims":[{"text":"Rule text.","evidence_ids":["E1"],"kind":"DIRECT"}],"reason":"E1"
        },
        {
            "claims":[{"index":0,"supported":True,"reason":"supported"}],
            "all_supported":True,
            "answer_fully_covered":True,
            "coverage_reason":"claimed covered"
        }
    ])
    monkeypatch.setattr(answer,"chat_json",lambda system,user:next(responses))
    result=answer.ask("test",strict_audit=True)
    assert result.status=="PARTIAL"
    assert "every factual answer unit" in result.reason
