from __future__ import annotations


SELECTION_VERSION = "alpha6.2-v1"

_KIND_PREFERENCE = {
    "field": ("structured_field", "table", "structured_record", "prose", "pdf_prose"),
    "explanation": ("pdf_prose", "prose", "structured_record", "table", "structured_field"),
    "table": ("table", "structured_field", "structured_record", "prose", "pdf_prose"),
    "feature": ("prose", "pdf_prose", "structured_record", "structured_field", "table"),
}


def rank_evidence(candidates: list[dict], intent: str) -> list[dict]:
    """Diagnostic-only deterministic ranking; provider is only a final tie break."""
    order = _KIND_PREFERENCE.get(intent, _KIND_PREFERENCE["explanation"])
    kinds = {kind: i for i, kind in enumerate(order)}
    return sorted(candidates, key=lambda row: (
        kinds.get(row.get("evidence_kind"), len(kinds)),
        row.get("normalized_digest", ""),
        row.get("representation_id", ""),
        row.get("evidence_id", ""),
    ))
