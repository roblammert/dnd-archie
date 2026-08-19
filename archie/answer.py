from __future__ import annotations

from dataclasses import dataclass

from .config import settings
from .llm import chat_json
from .prompts import ANSWER_SYSTEM, AUDIT_SYSTEM
from .retrieve import Evidence, evidence_packet, search

VALID_STATUS = {"VERIFIED", "DERIVED", "PARTIAL", "NOT_IN_SRD"}


@dataclass
class AnswerResult:
    status: str
    answer: str
    claims: list
    evidence: list[Evidence]
    audit: dict | None
    reason: str


def _validate_shape(obj: dict, available: set[str]):
    if obj.get("status") not in VALID_STATUS:
        raise ValueError("Invalid answer status from model.")
    if not isinstance(obj.get("answer"), str):
        raise ValueError("Missing answer text.")
    claims = obj.get("claims", [])
    if not isinstance(claims, list):
        raise ValueError("Claims must be a list.")
    for i, claim in enumerate(claims):
        if not isinstance(claim, dict) or not isinstance(claim.get("text"), str):
            raise ValueError(f"Invalid claim {i}.")
        ids = claim.get("evidence_ids")
        if not isinstance(ids, list) or not ids:
            raise ValueError(f"Claim {i} has no evidence IDs.")
        bad = [x for x in ids if x not in available]
        if bad:
            raise ValueError(f"Claim {i} invented/invalid evidence IDs: {bad}")
        if claim.get("kind") not in {"DIRECT", "DERIVED"}:
            raise ValueError(f"Claim {i} has invalid kind.")
    if obj["status"] in {"VERIFIED", "DERIVED"} and not claims:
        raise ValueError("Verified/derived answer contains no auditable claims.")
    return claims


def _audit_failed(audit: dict, claim_count: int) -> tuple[bool, str]:
    if not isinstance(audit, dict):
        return True, "audit response was not an object"

    checks = audit.get("claims", [])
    supported = {
        x.get("index"): x.get("supported")
        for x in checks
        if isinstance(x, dict)
    }
    failed = [i for i in range(claim_count) if supported.get(i) is not True]
    if failed:
        return True, f"claim indexes rejected: {failed}"

    if audit.get("all_supported") is not True:
        return True, "auditor did not affirm all_supported"

    # v1.5: claims are not enough. The visible answer must contain no extra unaudited rules.
    if audit.get("answer_fully_covered") is not True:
        uncovered = audit.get("uncovered_rules", [])
        return True, f"player-facing answer contains uncovered rules: {uncovered}"

    return False, ""


def ask(question: str, character_text: str | None = None, strict_audit: bool | None = None) -> AnswerResult:
    evidence = search(question)
    if not evidence:
        return AnswerResult(
            "NOT_IN_SRD",
            "I could not retrieve enough SRD 5.2.1 evidence to verify that. This does not mean the rule or option does not exist elsewhere in D&D.",
            [], [], None, "No local SRD evidence retrieved.",
        )

    packet = evidence_packet(evidence)
    character = character_text or "(none)"
    user = (
        f"QUESTION:\n{question}\n\n"
        f"CHARACTER DATA (facts about the player character only):\n{character}\n\n"
        f"EVIDENCE PACKET:\n{packet}"
    )
    obj = chat_json(ANSWER_SYSTEM, user)
    claims = _validate_shape(obj, {e.evidence_id for e in evidence})

    do_audit = settings.strict_audit if strict_audit is None else strict_audit
    audit = None
    if do_audit and claims:
        audit_user = (
            f"PLAYER QUESTION:\n{question}\n\n"
            f"CHARACTER DATA:\n{character}\n\n"
            f"EVIDENCE PACKET:\n{packet}\n\n"
            f"PLAYER-FACING ANSWER:\n{obj['answer']}\n\n"
            "PROPOSED CLAIMS:\n"
            + "\n".join(f"{i}. {claim}" for i, claim in enumerate(claims))
        )
        audit = chat_json(AUDIT_SYSTEM, audit_user)
        failed, detail = _audit_failed(audit, len(claims))
        if failed:
            return AnswerResult(
                "PARTIAL",
                "I found relevant SRD material, but my evidence audit could not support the complete generated answer. I am refusing to guess. Try asking a narrower version of the question.",
                [], evidence, audit, f"Fail-closed audit: {detail}",
            )

    return AnswerResult(obj["status"], obj["answer"], claims, evidence, audit, obj.get("reason", ""))
