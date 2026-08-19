from archie.answer import _audit_failed


def test_audit_rejects_uncovered_player_facing_rule():
    audit = {
        "claims": [{"index": 0, "supported": True, "reason": "ok"}],
        "all_supported": True,
        "answer_fully_covered": False,
        "uncovered_rules": ["unsupported jump formula"],
    }
    failed, detail = _audit_failed(audit, 1)
    assert failed is True
    assert "uncovered" in detail


def test_audit_accepts_supported_and_fully_covered_answer():
    audit = {
        "claims": [{"index": 0, "supported": True, "reason": "ok"}],
        "all_supported": True,
        "answer_fully_covered": True,
        "uncovered_rules": [],
    }
    failed, _ = _audit_failed(audit, 1)
    assert failed is False
