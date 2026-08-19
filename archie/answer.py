from __future__ import annotations
from dataclasses import dataclass
from .retrieve import search, evidence_packet, Evidence
from .llm import chat_json
from .prompts import ANSWER_SYSTEM, AUDIT_SYSTEM
from .config import settings

VALID_STATUS={'VERIFIED','DERIVED','PARTIAL','NOT_IN_SRD'}

@dataclass
class AnswerResult:
    status:str
    answer:str
    claims:list
    evidence:list[Evidence]
    audit:dict|None
    reason:str

def _validate_shape(obj: dict, available: set[str]):
    if obj.get('status') not in VALID_STATUS: raise ValueError('Invalid answer status from model.')
    if not isinstance(obj.get('answer'),str): raise ValueError('Missing answer text.')
    claims=obj.get('claims',[])
    if not isinstance(claims,list): raise ValueError('Claims must be a list.')
    for i,c in enumerate(claims):
        if not isinstance(c,dict) or not isinstance(c.get('text'),str): raise ValueError(f'Invalid claim {i}.')
        ids=c.get('evidence_ids')
        if not isinstance(ids,list) or not ids: raise ValueError(f'Claim {i} has no evidence IDs.')
        bad=[x for x in ids if x not in available]
        if bad: raise ValueError(f'Claim {i} invented/invalid evidence IDs: {bad}')
        if c.get('kind') not in {'DIRECT','DERIVED'}: raise ValueError(f'Claim {i} has invalid kind.')
    # A positive rules answer without claims is not allowed.
    if obj['status'] in {'VERIFIED','DERIVED'} and not claims:
        raise ValueError('Verified/derived answer contains no auditable claims.')
    return claims

def ask(question: str, character_text: str|None=None, strict_audit: bool|None=None) -> AnswerResult:
    evidence=search(question)
    if not evidence:
        return AnswerResult('NOT_IN_SRD','I could not retrieve enough SRD 5.2.1 evidence to verify that. This does not mean the rule or option does not exist elsewhere in D&D.',[],[],None,'No local SRD evidence retrieved.')
    packet=evidence_packet(evidence)
    user=f"QUESTION:\n{question}\n\nCHARACTER DATA (facts about the player character only):\n{character_text or '(none)'}\n\nEVIDENCE PACKET:\n{packet}"
    obj=chat_json(ANSWER_SYSTEM,user)
    claims=_validate_shape(obj,{e.evidence_id for e in evidence})
    do_audit=settings.strict_audit if strict_audit is None else strict_audit
    audit=None
    if do_audit and claims:
        audit_user=f"CHARACTER DATA:\n{character_text or '(none)'}\n\nEVIDENCE PACKET:\n{packet}\n\nPROPOSED CLAIMS:\n"+"\n".join(f"{i}. {c}" for i,c in enumerate(claims))
        audit=chat_json(AUDIT_SYSTEM,audit_user)
        checks=audit.get('claims',[]) if isinstance(audit,dict) else []
        supported={x.get('index'):x.get('supported') for x in checks if isinstance(x,dict)}
        failed=[i for i in range(len(claims)) if supported.get(i) is not True]
        if failed:
            return AnswerResult('PARTIAL',
              'I found relevant SRD material, but my evidence audit could not support every rules claim in the generated answer. I am refusing to guess. Try asking a narrower version of the question.',
              [],evidence,audit,f'Fail-closed audit rejected claim indexes: {failed}')
    return AnswerResult(obj['status'],obj['answer'],claims,evidence,audit,obj.get('reason',''))
