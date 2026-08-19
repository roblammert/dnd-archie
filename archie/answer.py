from __future__ import annotations
from dataclasses import dataclass
from .retrieve import search, evidence_packet, Evidence
from .llm import chat_json, LLMContractError
from .prompts import ANSWER_SYSTEM, AUDIT_SYSTEM
from .config import settings

VALID_STATUS={'VERIFIED','DERIVED','PARTIAL','NOT_IN_SRD'}
VALID_KINDS={'DIRECT','DERIVED'}

@dataclass
class AnswerResult:
    status:str
    answer:str
    claims:list
    evidence:list[Evidence]
    audit:dict|None
    reason:str


def _normalize_contract(obj: dict) -> dict:
    """Normalize harmless formatting drift without inventing any evidence."""
    if not isinstance(obj, dict):
        return obj
    out=dict(obj)
    if isinstance(out.get('status'), str):
        out['status']=out['status'].strip().upper()
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
    return claims


def _safe_partial(evidence: list[Evidence], reason: str, audit: dict|None=None) -> AnswerResult:
    return AnswerResult(
        'PARTIAL',
        'I found relevant SRD material, but I could not produce a fully auditable answer. I am refusing to guess. Try asking the question again or using a narrower wording.',
        [], evidence, audit, reason
    )


def _generate_answer(user: str, available: set[str]):
    """Allow one bounded format-correction retry, then fail closed."""
    last_error='unknown model contract error'
    for attempt in range(2):
        prompt=user
        if attempt:
            prompt += (
                "\n\nFORMAT CORRECTION RETRY:\n"
                "Your prior response violated the required JSON/evidence contract. Regenerate the answer from the SAME evidence only. "
                "Every claim must have at least one exact evidence_ids value from the packet and kind must be exactly DIRECT or DERIVED. "
                "Do not add facts, evidence, or rules. Return JSON only."
            )
        try:
            obj=_normalize_contract(chat_json(ANSWER_SYSTEM,prompt))
            claims=_validate_shape(obj,available)
            return obj,claims,None
        except (LLMContractError,ValueError) as e:
            last_error=str(e)
    return None,None,last_error


def _audit_answer(audit_user: str, claim_count: int):
    """Audit once; malformed audits fail closed rather than crashing the CLI."""
    try:
        audit=chat_json(AUDIT_SYSTEM,audit_user)
    except LLMContractError as e:
        return None, f'auditor returned malformed JSON: {e}'
    if not isinstance(audit,dict):
        return audit,'auditor response is not a JSON object'
    checks=audit.get('claims',[])
    supported={x.get('index'):x.get('supported') for x in checks if isinstance(x,dict)}
    failed=[i for i in range(claim_count) if supported.get(i) is not True]
    coverage_ok=audit.get('answer_fully_covered') is True
    all_ok=audit.get('all_supported') is True
    units=audit.get('answer_units',[])
    units_ok=(isinstance(units,list) and len(units)>0 and
              all(isinstance(x,dict) and x.get('supported') is True for x in units))
    if failed or not coverage_ok or not all_ok or not units_ok:
        why=[]
        if failed: why.append(f'claim indexes rejected: {failed}')
        if not coverage_ok: why.append('player-facing answer contains unaudited or unsupported mechanics')
        if not units_ok: why.append('auditor did not certify every factual answer unit')
        if not all_ok and not failed: why.append('auditor did not certify all claims')
        return audit,'; '.join(why)
    return audit,None


def ask(question: str, character_text: str|None=None, strict_audit: bool|None=None) -> AnswerResult:
    evidence=search(question)
    if not evidence:
        return AnswerResult('NOT_IN_SRD','I could not retrieve enough SRD 5.2.1 evidence to verify that. This does not mean the rule or option does not exist elsewhere in D&D.',[],[],None,'No local SRD evidence retrieved.')
    packet=evidence_packet(evidence)
    user=f"QUESTION:\n{question}\n\nCHARACTER DATA (facts about the player character only):\n{character_text or '(none)'}\n\nEVIDENCE PACKET:\n{packet}"
    available={e.evidence_id for e in evidence}
    obj,claims,contract_error=_generate_answer(user,available)
    if contract_error:
        return _safe_partial(evidence,'Fail-closed model contract after one correction retry: '+contract_error)

    do_audit=settings.strict_audit if strict_audit is None else strict_audit
    audit=None
    if do_audit and claims:
        audit_user=(f"ORIGINAL QUESTION:\n{question}\n\nCHARACTER DATA:\n{character_text or '(none)'}\n\nEVIDENCE PACKET:\n{packet}"
                    f"\n\nPLAYER-FACING ANSWER:\n{obj['answer']}"
                    f"\n\nPROPOSED CLAIMS:\n"+"\n".join(f"{i}. {c}" for i,c in enumerate(claims)))
        audit,audit_error=_audit_answer(audit_user,len(claims))
        if audit_error:
            return _safe_partial(evidence,'Fail-closed audit: '+audit_error,audit)
    return AnswerResult(obj['status'],obj['answer'],claims,evidence,audit,obj.get('reason',''))
