import pytest

import archie.answer as answer


SUCCESS_CASES = (
    ("What is Fireball's range?", "FND-FIREBALL-E7479F8D94D9", "Fireball has a range of 150 feet."),
    ("What are an Aboleth's hit points?", "CAN-ABOLETH-AEC77598C324", "An Aboleth has 150 Hit Points."),
    ("What is an Aboleth's armor class in SRD 5.2.1?", "CAN-ABOLETH-AEC77598C324", "An Aboleth has Armor Class 17."),
    ("What is an Aboleth's challenge rating?", "FND-ABOLETH-82A16D88C381", "An Aboleth has Challenge Rating 10."),
    ("What is a Giant Fly?", "O5E-SRD-2024-CREATURES-SRD-2024-GIANT-FLY-EF9B6C7C-C01", "Giant Fly is an SRD creature entry."),
    ("What is an Elf?", "O5E-SRD-2024-SPECIES-SRD-2024-ELF-06178F42-C01", "Elf is an SRD species entry."),
    ("What is Resistance?", "CAN-RESISTANCE-E5B09B25A79E", "Resistance halves damage of the applicable type, rounded down."),
    ("What school of magic is Awaken?", "FND-AWAKEN-DA63EC8B3780", "Awaken is a Transmutation spell."),
)


def _audit_ok(claim_count):
    return {
        "premises": [],
        "premise_coverage_complete": True,
        "claims": [
            {"index": index, "supported": True, "reason": "directly stated"}
            for index in range(claim_count)
        ],
        "answer_units": [
            {
                "index": 0,
                "text": "supported answer",
                "supporting_claim_indexes": list(range(claim_count)),
                "supported": True,
                "reason": "covered",
            }
        ] if claim_count else [],
        "answer_fully_covered": True,
        "all_supported": True,
        "coverage_reason": "covered",
    }


@pytest.mark.parametrize("question,evidence_id,claim", SUCCESS_CASES)
def test_public_answer_service_acceptance_success(monkeypatch, question, evidence_id, claim):
    calls = []

    def fake_chat(system, user, **kwargs):
        calls.append((system, user))
        if system == answer.ANSWER_SYSTEM:
            assert evidence_id in user
            assert "authority_id=wotc:srd-5.2.1" in user
            return {
                "status": "VERIFIED",
                "answer": claim,
                "premises": [],
                "claims": [{"text": claim, "evidence_ids": [evidence_id], "kind": "DIRECT"}],
                "reason": "direct evidence",
            }
        return _audit_ok(1)

    monkeypatch.setattr(answer, "chat_json", fake_chat)
    result = answer.ask(question, strict_audit=True)

    assert result.status == "VERIFIED"
    assert result.claims[0]["evidence_ids"] == [evidence_id]
    assert result.source_mode == "single_authority"
    assert len(calls) == 2


@pytest.mark.parametrize("question", (
    "What is the casting time of Awaken?",
    "What is a Dart's weight?",
))
def test_public_answer_service_retained_conflicts_fail_closed(monkeypatch, question):
    monkeypatch.setattr(
        answer,
        "chat_json",
        lambda *args, **kwargs: pytest.fail("conflicted evidence must not reach generation"),
    )
    result = answer.ask(question, strict_audit=True)
    assert result.status == "PARTIAL"
    assert "Fail-closed source conflict" in result.reason


def test_public_answer_service_acid_ambiguity_remains_unavailable(monkeypatch):
    def fake_chat(system, user, **kwargs):
        if system == answer.ANSWER_SYSTEM:
            return {
                "status": "NOT_IN_SRD",
                "answer": "The supplied evidence does not establish a single entry named Acid.",
                "premises": [],
                "claims": [],
                "reason": "Only differently named entries were retrieved.",
            }
        return _audit_ok(0)

    monkeypatch.setattr(answer, "chat_json", fake_chat)
    result = answer.ask("What is Acid?", strict_audit=True)
    assert result.status == "NOT_IN_SRD"
    assert result.claims == []


@pytest.mark.parametrize("question", (
    "Show me the Sorcerer progression table.",
    "Sorcerer class table.",
    "Sorcerer progression.",
))
def test_public_answer_service_uses_auditable_sorcerer_progression(monkeypatch, question):
    evidence_id = "CAN-SORCERER-9CDE7E69A664"
    monkeypatch.setattr(
        answer,
        "chat_json",
        lambda *args, **kwargs: pytest.fail("structured progression tables must not require model transcription"),
    )
    result = answer.ask(question, strict_audit=True)
    assert result.status == "VERIFIED"
    assert result.claims[0]["evidence_ids"] == [evidence_id]
    assert result.audit["kind"] == "deterministic_table_serialization"
    assert result.audit["rows_rendered"] == 20
    assert "| 1 | +2 | Spellcasting, Innate Sorcery |" in result.answer
    assert "| 20 | +6 | Arcane Apotheosis |" in result.answer


def test_public_answer_service_explain_sorcerer_prefers_prose(monkeypatch):
    evidence_id = "FND-SORCERER-34B1F8F4815E"

    def fake_chat(system, user, **kwargs):
        if system == answer.ANSWER_SYSTEM:
            assert user.index(evidence_id) < user.index("CAN-SORCERER-74B5009ABB32")
            return {
                "status": "VERIFIED",
                "answer": "The supplied prose describes the Sorcerer class.",
                "premises": [],
                "claims": [{
                    "text": "The supplied prose describes the Sorcerer class.",
                    "evidence_ids": [evidence_id],
                    "kind": "DIRECT",
                }],
                "reason": "class prose",
            }
        return _audit_ok(1)

    monkeypatch.setattr(answer, "chat_json", fake_chat)
    result = answer.ask("Explain Sorcerer.", strict_audit=True)
    assert result.status == "VERIFIED"
    assert result.claims[0]["evidence_ids"] == [evidence_id]
