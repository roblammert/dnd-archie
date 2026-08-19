import archie.answer as answer
from archie.llm import LLMContractError
from archie.retrieve import Evidence
from archie.prompts import AUDIT_REPAIR_SYSTEM


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
        "answer_units": [{"index": 0,"text": "Rule text.","supporting_claim_indexes": [0],"supported": True,"reason": "covered"}],
        "all_supported": True,
        "answer_fully_covered": True,
        "coverage_reason": "covered",
    }


def test_audit_repair_uses_compact_system_and_records_success(monkeypatch):
    monkeypatch.setattr(answer, "search", lambda q: _evidence())
    calls=[]
    def fake_chat(system,user):
        calls.append((system,user))
        if len(calls)==1:
            return _answer_obj()
        if len(calls)==2:
            raise LLMContractError("Model did not return valid JSON.")
        if len(calls)==3:
            assert system == AUDIT_REPAIR_SYSTEM
            assert "Required premise indexes exactly once: []" in user
            assert "Required claim indexes exactly once: [0]" in user
            return _audit_ok()
        raise AssertionError("unexpected call")
    monkeypatch.setattr(answer,"chat_json",fake_chat)
    result=answer.ask("test",strict_audit=True)
    assert result.status=="VERIFIED"
    assert "Audit structured-output correction succeeded." in result.reason
    assert len(calls)==3


def test_audit_repair_exhaustion_is_explicit(monkeypatch):
    monkeypatch.setattr(answer, "search", lambda q: _evidence())
    calls={"n":0}
    def fake_chat(system,user):
        calls["n"]+=1
        if calls["n"]==1:
            return _answer_obj()
        raise LLMContractError("Model did not return valid JSON.")
    monkeypatch.setattr(answer,"chat_json",fake_chat)
    result=answer.ask("test",strict_audit=True)
    assert result.status=="PARTIAL"
    assert "initial audit malformed" in result.reason
    assert "correction retry also malformed" in result.reason
    assert calls["n"]==3
