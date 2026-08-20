from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable


AUTHORITY_ORDER = {
    'official_srd': 100,
    'approved_supplement': 80,
    'house_rule': 70,
}


@dataclass(frozen=True)
class SourceUse:
    source_id: str
    authority_type: str
    edition: str | None
    evidence_ids: tuple[str, ...]
    authority_id: str | None = None
    representation_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        data = asdict(self)
        data['evidence_ids'] = list(self.evidence_ids)
        data['representation_ids'] = list(self.representation_ids)
        return data


def _claim_evidence_ids(claims: list[dict] | None) -> set[str]:
    ids: set[str] = set()
    for claim in claims or []:
        for evidence_id in claim.get('evidence_ids', []) if isinstance(claim, dict) else []:
            if isinstance(evidence_id, str) and evidence_id:
                ids.add(evidence_id)
    return ids


def source_usage(evidence: Iterable, claims: list[dict] | None = None) -> tuple[str, list[SourceUse]]:
    """Return deterministic source mode and the sources actually cited by the answer.

    When claims are supplied, only evidence IDs cited by those claims count as used.
    This prevents retrieved-but-unused sources from appearing in player-facing provenance.
    """
    items = list(evidence)
    cited_ids = _claim_evidence_ids(claims)
    if claims is not None:
        items = [e for e in items if getattr(e, 'evidence_id', None) in cited_ids]

    # Compatibility for historical callers constructing Evidence without the
    # alpha.6 authority identity fields.
    if any(getattr(e, 'authority_id', None) is None for e in items):
        legacy = {}
        for e in items:
            key = (getattr(e, 'source_id', 'unknown'), getattr(e, 'authority_type', 'unknown'), getattr(e, 'edition', None))
            legacy.setdefault(key, []).append(getattr(e, 'evidence_id', ''))
        uses = [SourceUse(source_id, authority, edition, tuple(dict.fromkeys(x for x in ids if x)))
                for (source_id, authority, edition), ids in legacy.items()]
        uses.sort(key=lambda x: (-AUTHORITY_ORDER.get(x.authority_type, 0), x.source_id))
        authorities = {u.authority_type for u in uses}
        mode = ('none' if not uses else 'official_only' if authorities == {'official_srd'}
                else 'supplemental_only' if 'official_srd' not in authorities else 'mixed')
        return mode, uses

    grouped: dict[tuple[str, str | None], dict[str, list[str]]] = {}
    for e in items:
        authority_id = getattr(e, 'authority_id', None)
        key = (authority_id or getattr(e, 'source_id', 'unknown'), getattr(e, 'edition', None))
        group = grouped.setdefault(key, {'evidence': [], 'representations': []})
        group['evidence'].append(getattr(e, 'evidence_id', ''))
        group['representations'].append(getattr(e, 'representation_id', None) or getattr(e, 'source_id', 'unknown'))

    uses = [
        SourceUse(authority_id, 'official_srd', edition,
                  tuple(dict.fromkeys(x for x in data['evidence'] if x)), authority_id,
                  tuple(sorted(set(data['representations']))))
        for (authority_id, edition), data in grouped.items()
    ]
    uses.sort(key=lambda x: (-AUTHORITY_ORDER.get(x.authority_type, 0), x.source_id))

    authorities = {u.authority_type for u in uses}
    if not uses:
        mode = 'none'
    elif authorities == {'official_srd'}:
        mode = 'official_only'
    elif 'official_srd' not in authorities:
        mode = 'supplemental_only'
    else:
        mode = 'mixed'
    return mode, uses


def format_source_note(mode: str, sources: list[SourceUse]) -> str:
    if not sources:
        return ''
    labels = ', '.join(
        f"{s.source_id} [{s.authority_type}{', '+s.edition if s.edition else ''}]"
        for s in sources
    )
    return f"Authority mode: {mode}. Sources used: {labels}."
