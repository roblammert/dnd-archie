from __future__ import annotations
from dataclasses import dataclass
import re
from .retrieve import search, evidence_packet, Evidence
from .llm import chat_json, LLMContractError
from .prompts import ANSWER_SYSTEM, AUDIT_SYSTEM, AUDIT_REPAIR_SYSTEM
from .config import settings

VALID_STATUS={'VERIFIED','DERIVED','PARTIAL','NOT_IN_SRD'}
VALID_KINDS={'DIRECT','DERIVED'}
VALID_PREMISE_STATES={'SUPPORTED','CONTRADICTED','UNRESOLVED'}


PREMISE_CUE_PATTERNS = (
    r"\bbecause\b",
    r"\bsince\b",
    r"\bthat means\b",
    r"\bdoes that mean\b",
    r"\bso that means\b",
    r"\btherefore\b",
    r"\bright\s*\?\s*$",
    r"\bcorrect\s*\?\s*$",
)

ABSENCE_INFERENCE_PATTERNS = (
    r"\bdon't say\b", r"\bdoesn't say\b", r"\bdo not say\b", r"\bdoes not say\b",
    r"\bdon't mention\b", r"\bdoesn't mention\b", r"\bdo not mention\b", r"\bdoes not mention\b",
    r"\bonly describe\b", r"\bonly describes\b", r"\bonly say\b", r"\bonly says\b",
    r"\bnot listed\b", r"\bisn't listed\b", r"\bnot included\b", r"\bisn't included\b",
)


# Broad propositions that must not be settled from a narrower related rule alone.
# These are semantic guardrails, not D&D rules.
FORCED_UNRESOLVED_PATTERNS = (
    (
        r"\binvisible\b.*(?:nobody|no one|never|ever|impossible).*\btarget",
        "Invisible creatures cannot ever be targeted",
    ),
    (
        r"\binvisible\b.*\battack(?:s| roll)?\b.*\b(?:automatically|always)\b.*\bmiss",
        "Attacks against an Invisible creature automatically miss",
    ),
    (
        r"\bprone\b.*\b(?:definitely|therefore|that means)\b.*\b(?:allowed|can)\b.*\b(?:bow|longbow|fire|attack)",
        "Being Prone definitely permits the stated bow attack",
    ),
)

# Direct permission questions can express the same unsupported inference without an
# explicit premise cue (for example, "Can I use a longbow while Prone?").
# Keep these guards narrow: they are semantic non-entailment protections, not a
# blanket rule that every "Can I" question is unresolved.
PERMISSION_UNRESOLVED_PATTERNS = (
    (
        r"^(?:can|may)\s+i\b.*\b(?:bow|longbow)\b.*\bprone\b",
        "Being Prone permits the stated bow attack",
    ),
    (
        r"^(?:am\s+i\s+allowed|is\s+it\s+allowed|is\s+it\s+legal)\b.*\b(?:bow|longbow)\b.*\bprone\b",
        "Being Prone permits the stated bow attack",
    ),
    (
        r"^while\s+prone\b.*(?:can|may)\s+i\b.*\b(?:bow|longbow)\b",
        "Being Prone permits the stated bow attack",
    ),
)


def forced_unresolved_premise(question: str) -> str|None:
    q=(question or '').strip().lower()
    for pattern, canonical in FORCED_UNRESOLVED_PATTERNS:
        if re.search(pattern,q):
            return canonical
    for pattern, canonical in PERMISSION_UNRESOLVED_PATTERNS:
        if re.search(pattern,q):
            return canonical
    return None


def absence_inference_guard(question: str) -> bool:
    q=(question or '').strip().lower()
    has_absence=any(re.search(p,q) for p in ABSENCE_INFERENCE_PATTERNS)
    has_inference=any(token in q for token in ('that means','does that mean','therefore','right?','correct?'))
    return has_absence and has_inference


def premise_mode(question: str) -> str:
    """Return REQUIRED only when the player explicitly asserts/presupposes a material proposition.

    Ordinary interrogatives and explicit character/numeric inputs are not premises. This keeps
    the epistemic layer from hijacking normal rules lookups and calculations.
    """
    q=(question or '').strip().lower()
    return 'REQUIRED' if any(re.search(p, q) for p in PREMISE_CUE_PATTERNS) else 'NONE'


def _render_unresolved_answer(premises: list[dict], claims: list[dict]) -> str:
    unresolved=[p for p in premises if p.get('state')=='UNRESOLVED']
    if not unresolved:
        return ''
    quoted='; '.join(f'“{p["text"].strip()}”' for p in unresolved)
    if claims:
        established=' '.join(c['text'].strip().rstrip('.')+'.' for c in claims)
        return f"I can't verify this premise from SRD 5.2.1: {quoted} What the SRD evidence does establish is: {established}"
    return f"I can't verify this premise from SRD 5.2.1: {quoted}"



def _apply_forced_unresolved_premise(premises: list[dict], forced_text: str|None) -> list[dict]:
    """Override broad inference premises that the SRD evidence does not settle."""
    if not forced_text:
        return premises
    return [{"text": forced_text, "state": "UNRESOLVED", "evidence_ids": []}]


def _claim_settles_forced_premise(claim_text: str, forced_text: str|None) -> bool:
    """Reject claims that directly resolve a forced-UNRESOLVED proposition either way."""
    if not forced_text:
        return False
    c=(claim_text or '').lower()
    f=forced_text.lower()
    if 'target' in f:
        broad=(
            r"\b(?:can|cannot|can't|may|may not|impossible to|possible to)\b.*\btarget",
            r"\btarget(?:ed|ing)?\b.*\b(?:allowed|forbidden|possible|impossible)\b",
        )
        return any(re.search(p,c) for p in broad)
    if 'automatically miss' in f:
        return bool(re.search(r"\b(?:automatically|always|never)\b.*\b(?:hit|miss)",c))
    if 'permits' in f or 'bow attack' in f:
        return bool(re.search(r"\b(?:allowed|permitted|can|cannot|can't)\b.*\b(?:bow|longbow|attack|fire)",c))
    return False


def _filter_claims_for_unresolved(claims: list[dict], forced_text: str|None) -> list[dict]:
    if not forced_text:
        return claims
    return [c for c in claims if not _claim_settles_forced_premise(c.get('text',''),forced_text)]

@dataclass
class AnswerResult:
    status:str
    answer:str
    claims:list
    evidence:list[Evidence]
    audit:dict|None
    reason:str
    premises:list|None=None


def _normalize_contract(obj: dict) -> dict:
    """Normalize harmless formatting drift without inventing any evidence."""
    if not isinstance(obj, dict):
        return obj
    out=dict(obj)
    if isinstance(out.get('status'), str):
        out['status']=out['status'].strip().upper()
    premises=out.get('premises')
    if isinstance(premises, list):
        normalized_premises=[]
        for premise in premises:
            if not isinstance(premise, dict):
                normalized_premises.append(premise)
                continue
            pr=dict(premise)
            if isinstance(pr.get('state'), str):
                pr['state']=pr['state'].strip().upper()
            if isinstance(pr.get('evidence_ids'), list):
                pr['evidence_ids']=[x.strip() if isinstance(x,str) else x for x in pr['evidence_ids']]
            normalized_premises.append(pr)
        out['premises']=normalized_premises
    claims=out.get('claims')
    if isinstance(claims, list):
        normalized=[]
        for claim in claims:
            if not isinstance(claim, dict):
                normalized.append(claim)
                continue
            c=dict(claim)
            if isinstance(c.get('kind'), str):
                c['kind']=c['kind'].strip().upper()
            if isinstance(c.get('evidence_ids'), list):
                c['evidence_ids']=[x.strip() if isinstance(x,str) else x for x in c['evidence_ids']]
            normalized.append(c)
        out['claims']=normalized
    return out


def _validate_shape(obj: dict, available: set[str]):
    if not isinstance(obj,dict): raise ValueError('Model response is not a JSON object.')
    if obj.get('status') not in VALID_STATUS: raise ValueError('Invalid answer status from model.')
    if not isinstance(obj.get('answer'),str): raise ValueError('Missing answer text.')
    claims=obj.get('claims',[])
    if not isinstance(claims,list): raise ValueError('Claims must be a list.')
    for i,c in enumerate(claims):
        if not isinstance(c,dict) or not isinstance(c.get('text'),str): raise ValueError(f'Invalid claim {i}.')
        ids=c.get('evidence_ids')
        if not isinstance(ids,list) or not ids: raise ValueError(f'Claim {i} has no evidence IDs.')
        if not all(isinstance(x,str) and x for x in ids): raise ValueError(f'Claim {i} has invalid evidence IDs.')
        bad=[x for x in ids if x not in available]
        if bad: raise ValueError(f'Claim {i} invented/invalid evidence IDs: {bad}')
        if c.get('kind') not in VALID_KINDS: raise ValueError(f'Claim {i} has invalid kind.')
    if obj['status'] in {'VERIFIED','DERIVED'} and not claims:
        raise ValueError('Verified/derived answer contains no auditable claims.')
    premises=obj.get('premises',[])
    if not isinstance(premises,list): raise ValueError('Premises must be a list.')
    for i,premise in enumerate(premises):
        if not isinstance(premise,dict) or not isinstance(premise.get('text'),str) or not premise.get('text').strip():
            raise ValueError(f'Invalid premise {i}.')
        state=premise.get('state')
        if state not in VALID_PREMISE_STATES:
            raise ValueError(f'Premise {i} has invalid state.')
        ids=premise.get('evidence_ids',[])
        if not isinstance(ids,list) or not all(isinstance(x,str) and x for x in ids):
            raise ValueError(f'Premise {i} has invalid evidence IDs.')
        bad=[x for x in ids if x not in available]
        if bad: raise ValueError(f'Premise {i} invented/invalid evidence IDs: {bad}')
        if state in {'SUPPORTED','CONTRADICTED'} and not ids:
            raise ValueError(f'Premise {i} state {state} requires evidence IDs.')
        if state=='UNRESOLVED' and ids:
            raise ValueError(f'Premise {i} state UNRESOLVED must not claim evidentiary support.')
    if any(p.get('state')=='UNRESOLVED' for p in premises) and obj['status'] in {'VERIFIED','DERIVED'}:
        raise ValueError('An answer with an UNRESOLVED material premise cannot be VERIFIED or DERIVED.')
    return claims



def _validate_premise_mode(premises: list[dict], mode: str, absence_guard: bool=False) -> None:
    if mode == 'NONE' and premises:
        raise ValueError('Ordinary question must not contain premise classifications.')
    if mode == 'REQUIRED' and not premises:
        raise ValueError('Premise-bearing question requires a material premise classification.')
    if absence_guard and any(p.get('state') != 'UNRESOLVED' for p in premises):
        raise ValueError('Absence-of-evidence inference must remain UNRESOLVED unless separately established outside the absence inference.')


def _safe_partial(evidence: list[Evidence], reason: str, audit: dict|None=None) -> AnswerResult:
    return AnswerResult(
        'PARTIAL',
        'I found relevant SRD material, but I could not produce a fully auditable answer. I am refusing to guess. Try asking the question again or using a narrower wording.',
        [], evidence, audit, reason, []
    )


def _generate_answer(user: str, available: set[str], mode: str, absence_guard: bool=False, forced_premise: str|None=None):
    """Allow one bounded format-correction retry, then fail closed."""
    last_error='unknown model contract error'
    for attempt in range(2):
        prompt=user
        if attempt:
            prompt += (
                "\n\nFORMAT CORRECTION RETRY:\n"
                "Your prior response violated the required JSON/evidence contract. Regenerate the answer from the SAME evidence only. "
                "Every claim must have at least one exact evidence_ids value from the packet and kind must be exactly DIRECT or DERIVED. "
                "Premise state must be SUPPORTED, CONTRADICTED, or UNRESOLVED; UNRESOLVED premises must use an empty evidence_ids list. "
                "If PREMISE MODE is NONE, premises must be []. If PREMISE MODE is REQUIRED, include the material asserted/presupposed proposition and do not classify character data or numeric inputs as premises. Do not add facts, evidence, or rules. Return JSON only."
            )
        try:
            obj=_normalize_contract(chat_json(ANSWER_SYSTEM,prompt))
            if forced_premise and isinstance(obj,dict):
                raw_claims=obj.get('claims',[]) if isinstance(obj.get('claims',[]),list) else []
                obj['premises']=_apply_forced_unresolved_premise([],forced_premise)
                obj['claims']=_filter_claims_for_unresolved(raw_claims,forced_premise)
                obj['status']='PARTIAL' if obj['claims'] else 'NOT_IN_SRD'
            claims=_validate_shape(obj,available)
            premises=obj.get('premises',[])
            _validate_premise_mode(premises,mode,absence_guard)
            return obj,claims,premises,None
        except (LLMContractError,ValueError) as e:
            last_error=str(e)
    return None,None,None,last_error


def _audit_answer(audit_user: str, claim_count: int, premise_count: int):
    """Audit once, then perform one compact structured-output repair attempt.

    Transport/server failures still propagate as operational errors. Only malformed
    structured output is retried. The return tuple is (audit, error, repair_used).
    """
    try:
        candidate=chat_json(AUDIT_SYSTEM,audit_user)
    except LLMContractError as e:
        initial_error=f'auditor returned malformed JSON: {e}'
    else:
        if isinstance(candidate,dict):
            audit=candidate
            initial_error=None
        else:
            audit=None
            initial_error='auditor response is not a JSON object'

    repair_used=False
    if initial_error is not None:
        repair_used=True
        premise_indexes=list(range(premise_count))
        claim_indexes=list(range(claim_count))
        repair_user=(audit_user+
            "\n\nAUDIT FORMAT CORRECTION RETRY / STRUCTURED-OUTPUT REPAIR:\n"
            f"Required premise indexes exactly once: {premise_indexes}\n"
            f"Required claim indexes exactly once: {claim_indexes}\n"
            "Re-audit the SAME material. Return only one JSON object matching the repair schema. "
            "Do not omit required indexes. Do not add D&D knowledge or alter the proposed answer."
        )
        try:
            repaired=chat_json(AUDIT_REPAIR_SYSTEM,repair_user)
        except LLMContractError as e:
            return None, (
                f'initial audit malformed ({initial_error}); correction retry also malformed: {e}'
            ), True
        if not isinstance(repaired,dict):
            return None, (
                f'initial audit malformed ({initial_error}); correction retry also malformed: auditor response is not a JSON object'
            ), True
        audit=repaired

    checks=audit.get('claims',[])
    supported={x.get('index'):x.get('supported') for x in checks if isinstance(x,dict)}
    failed=[i for i in range(claim_count) if supported.get(i) is not True]
    coverage_ok=audit.get('answer_fully_covered') is True
    all_ok=audit.get('all_supported') is True
    premise_coverage_ok=audit.get('premise_coverage_complete') is True
    units=audit.get('answer_units',[])
    units_ok=(isinstance(units,list) and
              all(isinstance(x,dict) and x.get('supported') is True for x in units) and
              (len(units)>0 or claim_count==0))
    premise_checks=audit.get('premises',[])
    premise_supported={x.get('index'):x.get('classification_valid') for x in premise_checks if isinstance(x,dict)}
    failed_premises=[i for i in range(premise_count) if premise_supported.get(i) is not True]
    if failed or failed_premises or not premise_coverage_ok or not coverage_ok or not all_ok or not units_ok:
        why=[]
        if failed: why.append(f'claim indexes rejected: {failed}')
        if failed_premises: why.append(f'premise classifications rejected: {failed_premises}')
        if not premise_coverage_ok: why.append('material question premises were not fully classified')
        if not coverage_ok: why.append('player-facing answer contains unaudited or unsupported mechanics')
        if not units_ok: why.append('auditor did not certify every factual answer unit')
        if not all_ok and not failed: why.append('auditor did not certify all claims')
        return audit,'; '.join(why),repair_used
    return audit,None,repair_used

def ask(question: str, character_text: str|None=None, strict_audit: bool|None=None) -> AnswerResult:
    evidence=search(question)
    if not evidence:
        return AnswerResult('NOT_IN_SRD','I could not retrieve enough SRD 5.2.1 evidence to verify that. This does not mean the rule or option does not exist elsewhere in D&D.',[],[],None,'No local SRD evidence retrieved.',[])
    packet=evidence_packet(evidence)
    mode=premise_mode(question)
    absence_guard=absence_inference_guard(question)
    forced_premise=forced_unresolved_premise(question)
    if forced_premise:
        mode='REQUIRED'
    user=(f"QUESTION:\n{question}\n\nPREMISE MODE: {mode}\nABSENCE-INFERENCE GUARD: {'ACTIVE' if absence_guard else 'INACTIVE'}\n"
          f"FORCED UNRESOLVED PREMISE: {forced_premise or '(none)'}\n"
          "If PREMISE MODE is NONE, premises MUST be []. If REQUIRED, classify only the material proposition the player asserted or presupposed; do not classify supplied character data, numeric inputs, or the interrogative itself as a premise. If FORCED UNRESOLVED PREMISE is present, that exact proposition must remain UNRESOLVED; do not assert it or its negation.\n"
          f"\nCHARACTER DATA (facts about the player character only):\n{character_text or '(none)'}\n\nEVIDENCE PACKET:\n{packet}")
    available={e.evidence_id for e in evidence}
    obj,claims,premises,contract_error=_generate_answer(user,available,mode,absence_guard,forced_premise)
    if contract_error:
        return _safe_partial(evidence,'Fail-closed model contract after one correction retry: '+contract_error)

    do_audit=settings.strict_audit if strict_audit is None else strict_audit
    audit=None
    if any(p.get('state')=='UNRESOLVED' for p in premises):
        obj['status']='PARTIAL' if claims else 'NOT_IN_SRD'
        obj['answer']=_render_unresolved_answer(premises,claims)
        obj['reason']='The material premise is unresolved by the supplied SRD evidence; only independently supported claims are stated.'
    if do_audit:
        audit_user=(f"ORIGINAL QUESTION:\n{question}\n\nPREMISE MODE: {mode}\nABSENCE-INFERENCE GUARD: {'ACTIVE' if absence_guard else 'INACTIVE'}\nFORCED UNRESOLVED PREMISE: {forced_premise or '(none)'}\n\nCHARACTER DATA:\n{character_text or '(none)'}\n\nEVIDENCE PACKET:\n{packet}"
                    f"\n\nPLAYER-FACING ANSWER:\n{obj['answer']}"
                    f"\n\nPROPOSED PREMISES:\n"+"\n".join(f"{i}. {p}" for i,p in enumerate(premises))
                    +f"\n\nPROPOSED CLAIMS:\n"+"\n".join(f"{i}. {c}" for i,c in enumerate(claims)))
        audit,audit_error,audit_repair_used=_audit_answer(audit_user,len(claims),len(premises))
        if audit_error:
            return _safe_partial(evidence,'Fail-closed audit: '+audit_error,audit)
        if audit_repair_used:
            base_reason=obj.get('reason','').strip()
            repair_note='Audit structured-output correction succeeded.'
            obj['reason']=(base_reason+' '+repair_note).strip()
    return AnswerResult(obj['status'],obj['answer'],claims,evidence,audit,obj.get('reason',''),premises)
