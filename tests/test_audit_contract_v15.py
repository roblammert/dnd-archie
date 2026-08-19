from archie.answer import _validate_shape
import pytest

def test_positive_answer_still_requires_claims():
    with pytest.raises(ValueError):
        _validate_shape({"status":"VERIFIED","answer":"A rule.","claims":[]},{"E1"})

def test_invalid_evidence_still_fails_closed():
    with pytest.raises(ValueError):
        _validate_shape({"status":"VERIFIED","answer":"A rule.","claims":[{"text":"A rule.","evidence_ids":["NOPE"],"kind":"DIRECT"}]},{"E1"})

def test_ask_fails_closed_when_answer_has_uncovered_mechanic(monkeypatch):
    import archie.answer as mod
    from archie.retrieve import Evidence

    evidence=[Evidence("E1",1,"1","Test","Rule text.",1.0)]
    monkeypatch.setattr(mod, "search", lambda question: evidence)
    responses=iter([
        {
            "status":"VERIFIED",
            "answer":"Supported rule plus an extra unsupported mechanic.",
            "claims":[{"text":"Supported rule.","evidence_ids":["E1"],"kind":"DIRECT"}],
            "reason":"E1"
        },
        {
            "claims":[{"index":0,"supported":True,"reason":"supported"}],
            "all_supported":True,
            "answer_fully_covered":False,
            "coverage_reason":"extra mechanic is not represented by a claim"
        }
    ])
    monkeypatch.setattr(mod, "chat_json", lambda system,user: next(responses))
    result=mod.ask("test",strict_audit=True)
    assert result.status == "PARTIAL"
    assert "unsupported mechanics" in result.reason
