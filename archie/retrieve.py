from __future__ import annotations
import re
from dataclasses import dataclass, asdict
from .db import connect
from .config import settings
from .source import verify_source

@dataclass
class Evidence:
    evidence_id: str
    page_pdf: int
    page_label: str
    heading: str
    text: str
    score: float
    def to_dict(self): return asdict(self)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at",
    "be", "been", "being", "but", "by",
    "can", "could",
    "did", "do", "does",
    "for", "from",
    "had", "has", "have", "how",
    "i", "if", "in", "into", "is", "it",
    "me", "my",
    "of", "on", "or",
    "that", "the", "their", "them", "then", "there",
    "these", "they", "this", "those", "to",
    "was", "were", "what", "when", "where", "which",
    "who", "why", "will", "with", "would",
    "you", "your",
    "happen", "happens", "happened",
}


def _fts_query(q: str) -> str:
    terms = re.findall(r"[A-Za-z0-9']+", q.lower())

    useful = [
        term
        for term in terms
        if term not in STOPWORDS and len(term) > 1
    ]

    if not useful:
        useful = terms

    # Preserve original order while removing duplicates.
    useful = list(dict.fromkeys(useful))

    return " OR ".join(
        f'"{term.replace(chr(34), chr(34) * 2)}"'
        for term in useful[:20]
    )


def search(query: str, top_k: int|None=None) -> list[Evidence]:
    verify_source()
    if not settings.database.exists():
        raise RuntimeError('SRD index not found. Run: python -m archie.cli ingest')
    c=connect()
    meta=dict(c.execute('SELECT key,value FROM metadata').fetchall())
    from .source import load_manifest
    expected=load_manifest()['sha256']
    if meta.get('source_sha256') != expected:
        c.close()
        raise RuntimeError('SRD index does not match the approved source. Run: python -m archie.cli ingest')
    iq=_fts_query(query)
    if not iq:
        c.close(); return []
    rows=c.execute("""
      SELECT c.evidence_id,c.page_pdf,c.page_label,c.heading,c.text,
             bm25(chunks_fts, 0.0, 3.0, 1.0) AS rank
      FROM chunks_fts JOIN chunks c ON c.id=chunks_fts.rowid
      WHERE chunks_fts MATCH ?
      ORDER BY rank LIMIT ?
    """,(iq, top_k or settings.top_k)).fetchall()
    c.close()
    return [Evidence(r['evidence_id'],r['page_pdf'],r['page_label'],r['heading'],r['text'],float(r['rank'])) for r in rows]

def evidence_packet(items: list[Evidence]) -> str:
    parts=[]
    for e in items:
        parts.append(f"[{e.evidence_id}] PDF page {e.page_pdf} | {e.heading}\n{e.text}")
    return '\n\n---\n\n'.join(parts)
