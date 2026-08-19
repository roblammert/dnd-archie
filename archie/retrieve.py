from __future__ import annotations
import re
from dataclasses import dataclass, asdict, field
from .db import connect
from .config import settings
from .source import verify_source, get_source_manifest
from .concepts import CONCEPTS, ALIASES

STOPWORDS = {
    'a','an','and','are','as','at','be','been','being','but','by','can','could','did','do','does',
    'for','from','had','has','have','how','i','if','in','into','is','it','me','my','of','on','or',
    'that','the','their','them','then','there','these','they','this','those','to','was','were','what',
    'when','where','which','who','why','will','with','would','you','your','happen','happens','happened',
    'right','work','works','working','thing','things','specific','rules','rule'
}

@dataclass
class Evidence:
    evidence_id: str
    page_pdf: int | None
    page_label: str | None
    heading: str
    text: str
    score: float
    source_id: str = 'srd521'
    authority_type: str = 'official_srd'
    edition: str | None = '2024'
    origin: str = 'primary'
    matched_by: list[str] = field(default_factory=list)
    def to_dict(self):
        return asdict(self)

@dataclass
class QueryPlan:
    original: str
    terms: list[str]
    concepts: list[str]
    aliases: list[str]
    subqueries: list[str]
    def to_dict(self):
        return asdict(self)

def _tokens(q: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", q.lower())

def _find_aliases(q: str) -> list[str]:
    lower = q.lower()
    found=[]
    for alias, expansions in ALIASES.items():
        if alias in lower:
            found.extend(expansions)
    return list(dict.fromkeys(found))

def _find_concepts(q: str, alias_expansions: list[str]) -> list[str]:
    lower = q.lower()
    found=[]
    for key in sorted(CONCEPTS, key=len, reverse=True):
        if re.search(rf'\b{re.escape(key)}\b', lower):
            found.append(key)
    for expansion in alias_expansions:
        if expansion in CONCEPTS and expansion not in found:
            found.append(expansion)
    # Comparison questions need both sides represented independently.
    if 'saving throw' in lower and 'ability check' in lower:
        for x in ('ability check','saving throw'):
            if x not in found: found.append(x)
    return found

def build_query_plan(q: str) -> QueryPlan:
    aliases=_find_aliases(q)
    lower=q.lower()
    # Deterministic intent bridges for common natural-language phrasing.
    if 'move' in lower and 'before' in lower and 'after' in lower and 'breaking up your move' not in aliases:
        aliases.append('breaking up your move')
    if ('leveled spell' in lower or 'levelled spell' in lower) and 'spell slot per turn' not in aliases:
        aliases.append('spell slot per turn')
    if 'natural 20' in lower and 'natural 20' not in aliases:
        aliases.append('natural 20')
    if 'natural 1' in lower and 'natural 1' not in aliases:
        aliases.append('natural 1')
    concepts=_find_concepts(q, aliases)
    terms=[t for t in _tokens(q) if len(t)>1 and t not in STOPWORDS]
    for expansion in aliases:
        terms.extend(_tokens(expansion))
    for concept in concepts:
        terms.extend(_tokens(CONCEPTS[concept]['canonical']))
    terms=list(dict.fromkeys(t for t in terms if t not in STOPWORDS))
    if not terms:
        terms=list(dict.fromkeys(_tokens(q)))
    subqueries=[]
    for concept in concepts:
        subqueries.append(CONCEPTS[concept]['canonical'])
    subqueries.extend(aliases)
    subqueries=list(dict.fromkeys(subqueries))
    return QueryPlan(q, terms[:24], concepts, aliases, subqueries)

def _escape(term: str) -> str:
    return term.replace('"','""')

def _fts_or(terms: list[str]) -> str:
    return ' OR '.join(f'"{_escape(t)}"' for t in terms if t)

def _fetch_fts(c, query: str, limit: int):
    if not query: return []
    return c.execute('''
      SELECT c.id,c.evidence_id,c.source_id,c.page_pdf,c.page_label,c.heading,c.text,
             s.authority_type,s.edition,s.priority,
             bm25(evidence_fts, 0.0, 3.0, 1.0) AS rank
      FROM evidence_fts
      JOIN evidence_chunks c ON c.id=evidence_fts.rowid
      JOIN sources s ON s.id=c.source_id
      WHERE evidence_fts MATCH ? AND s.enabled=1 AND s.approved=1 AND s.license_status='present'
        AND (s.edition IS NULL OR s.edition=?)
      ORDER BY rank LIMIT ?
    ''',(query,settings.active_edition,limit)).fetchall()

def _score_row(row, plan: QueryPlan, matched_by: str) -> float:
    text=row['text'].lower(); heading=row['heading']
    score=max(0.0, -float(row['rank']))
    # Alpha.4 authority precedence: higher-priority approved sources receive a modest
    # deterministic boost. This prefers the official PDF when equivalent evidence
    # exists, without suppressing supplemental evidence when the PDF has no match.
    score += max(0.0, float(row['priority']) - 70.0) / 20.0
    for term in plan.terms:
        if term in text:
            score += min(1.2, text.count(term)*0.15)
    for concept in plan.concepts:
        meta=CONCEPTS[concept]
        canonical=meta['canonical'].lower()
        if canonical in text:
            score += 4.0
        marker=meta.get('marker')
        if marker and marker.lower() in text:
            score += 12.0
        if heading in meta.get('sections',()):
            score += 4.0
        # Glossary-like definition starts are especially authoritative for named concepts.
        if re.search(rf'\b{re.escape(canonical)}\b(?:\s*\[[^\]]+\])?', text):
            score += 1.5
    if matched_by.startswith('exact:'):
        score += 5.0
    return score

def _verify_index(c):
    meta=dict(c.execute('SELECT key,value FROM metadata').fetchall())
    manifest=get_source_manifest(settings.source_id)
    expected=manifest.sha256
    if meta.get('source_sha256') != expected or meta.get('source_id') != manifest.id:
        raise RuntimeError('SRD index does not match the approved source. Run: python -m archie.cli ingest')

def search(query: str, top_k: int|None=None, *, expand_neighbors: bool=True) -> list[Evidence]:
    verify_source()
    if not settings.database.exists():
        raise RuntimeError('SRD index not found. Run: python -m archie.cli ingest')
    plan=build_query_plan(query)
    final_k=top_k or settings.top_k
    candidate_k=max(settings.retrieval_candidate_k, final_k*5)
    c=connect()
    try:
        _verify_index(c)
        candidates={}
        broad=_fts_or(plan.terms)
        for row in _fetch_fts(c,broad,candidate_k):
            candidates[row['id']]=(row,_score_row(row,plan,'broad'),['broad'])
        for sub in plan.subqueries:
            phrase='"'+_escape(sub.lower())+'"'
            for row in _fetch_fts(c,phrase,candidate_k):
                sc=_score_row(row,plan,f'exact:{sub}')
                old=candidates.get(row['id'])
                if old:
                    candidates[row['id']] = (row,max(old[1],sc),list(dict.fromkeys(old[2]+[f'exact:{sub}'])))
                else:
                    candidates[row['id']] = (row,sc,[f'exact:{sub}'])
        ranked_all=sorted(candidates.values(), key=lambda x:(-x[1], x[0]['id']))
        # Reserve one strong exact hit for each detected concept. This prevents a
        # comparison question from retrieving six excellent passages about one
        # side while omitting the other side entirely.
        selected=[]; selected_ids=set()
        for sub in plan.subqueries:
            tag=f'exact:{sub}'
            exact=[x for x in ranked_all if tag in x[2] and x[0]['id'] not in selected_ids]
            if exact and len(selected)<final_k:
                selected.append(exact[0]); selected_ids.add(exact[0][0]['id'])
        for item in ranked_all:
            if len(selected)>=final_k: break
            if item[0]['id'] in selected_ids: continue
            selected.append(item); selected_ids.add(item[0]['id'])
        selected.sort(key=lambda x:(-x[1], x[0]['id']))
        evidence=[]
        seen=set()
        primary_ids=[]
        for row,score,matched in selected:
            ev=Evidence(row['evidence_id'],row['page_pdf'],row['page_label'],row['heading'],row['text'],score,row['source_id'],row['authority_type'],row['edition'],'primary',matched)
            evidence.append(ev); seen.add(row['id']); primary_ids.append(row['id'])
        if expand_neighbors and settings.neighbor_radius>0:
            # Expand only around the strongest few hits to preserve context without flooding the packet.
            for rid in primary_ids[:min(3,len(primary_ids))]:
                rows=c.execute('''SELECT c.id,c.evidence_id,c.source_id,c.page_pdf,c.page_label,c.heading,c.text,s.authority_type,s.edition
                                  FROM evidence_chunks c JOIN sources s ON s.id=c.source_id
                                  WHERE c.id BETWEEN ? AND ? AND s.enabled=1 AND s.approved=1 AND s.license_status='present'
                                    AND (s.edition IS NULL OR s.edition=?) ORDER BY c.id''',
                               (max(1,rid-settings.neighbor_radius), rid+settings.neighbor_radius,settings.active_edition)).fetchall()
                for row in rows:
                    if row['id'] in seen: continue
                    evidence.append(Evidence(row['evidence_id'],row['page_pdf'],row['page_label'],row['heading'],row['text'],-999.0,row['source_id'],row['authority_type'],row['edition'],'context',[f'neighbor-of:{rid}']))
                    seen.add(row['id'])
        return evidence
    finally:
        c.close()

def diagnose(query: str, top_k: int|None=None) -> dict:
    plan=build_query_plan(query)
    items=search(query,top_k,expand_neighbors=True)
    return {
        'query': query,
        'plan': plan.to_dict(),
        'results': [x.to_dict() for x in items],
        'primary_count': sum(1 for x in items if x.origin=='primary'),
        'context_count': sum(1 for x in items if x.origin=='context'),
    }

def evidence_packet(items: list[Evidence]) -> str:
    parts=[]
    for e in items:
        role='PRIMARY HIT' if e.origin=='primary' else 'ADJACENT CONTEXT'
        location=f'PDF page {e.page_pdf}' if e.page_pdf is not None else f'record {e.page_label or e.evidence_id}'
        parts.append(f"[{e.evidence_id}] source={e.source_id} authority={e.authority_type} edition={e.edition or '-'} | {location} | {e.heading} | {role}\n{e.text}")
    return '\n\n---\n\n'.join(parts)
