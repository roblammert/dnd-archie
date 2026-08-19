from __future__ import annotations

import hashlib
import json
import re
from typing import Any

MAX_EVIDENCE_CHARS = 1800
SKIP_KEYS = {'document', 'url', 'permalink'}


def _slug(value: str) -> str:
    s=re.sub(r'[^A-Za-z0-9]+','-',value.upper()).strip('-')
    return s[:72] or 'RECORD'


def _scalar(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int,float,str)):
        return str(value).strip()
    return None


def _flatten(value: Any, prefix: str = '') -> list[str]:
    lines=[]
    if isinstance(value, dict):
        for key, item in value.items():
            if key in SKIP_KEYS:
                continue
            label=f"{prefix}.{key}" if prefix else str(key)
            scalar=_scalar(item)
            if scalar is not None:
                if scalar:
                    lines.append(f"{label}: {scalar}")
            else:
                lines.extend(_flatten(item,label))
    elif isinstance(value, list):
        scalars=[_scalar(x) for x in value]
        if all(x is not None for x in scalars):
            vals=[x for x in scalars if x]
            if vals:
                lines.append(f"{prefix}: {', '.join(vals)}")
        else:
            for idx,item in enumerate(value,1):
                lines.extend(_flatten(item,f"{prefix}[{idx}]"))
    return lines


def record_text(content_type: str, name: str, structured_json: str) -> str:
    obj=json.loads(structured_json)
    lines=[f"Name: {name}",f"Content type: {content_type}"]
    lines.extend(_flatten(obj))
    # Preserve order while removing exact duplicate lines.
    return '\n'.join(dict.fromkeys(x for x in lines if x.strip()))


def split_text(text: str, max_chars: int = MAX_EVIDENCE_CHARS) -> list[str]:
    lines=text.splitlines(); out=[]; cur=[]; size=0
    for line in lines:
        if cur and size+len(line)+1 > max_chars:
            out.append('\n'.join(cur)); cur=[]; size=0
        if len(line) > max_chars:
            # Large descriptions are split on sentence boundaries when possible.
            parts=re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])',line)
            for part in parts:
                if cur and size+len(part)+1 > max_chars:
                    out.append('\n'.join(cur)); cur=[]; size=0
                if len(part) > max_chars:
                    for i in range(0,len(part),max_chars):
                        piece=part[i:i+max_chars]
                        if cur: out.append('\n'.join(cur)); cur=[]; size=0
                        out.append(piece)
                else:
                    cur.append(part); size+=len(part)+1
        else:
            cur.append(line); size+=len(line)+1
    if cur: out.append('\n'.join(cur))
    return [x for x in out if x.strip()]


def materialize_structured_evidence(c, source_id: str) -> int:
    src=c.execute('SELECT id,provider,provider_document_key,edition,approved,enabled FROM sources WHERE id=?',(source_id,)).fetchone()
    if not src:
        raise ValueError(f'Unknown source: {source_id}')
    if not src['approved']:
        raise ValueError(f'Source is not approved: {source_id}')
    version=c.execute('SELECT id FROM source_versions WHERE source_id=? AND active=1',(source_id,)).fetchone()
    if not version:
        raise ValueError(f'No active source version: {source_id}')
    version_id=version['id']
    c.execute('DELETE FROM evidence_chunks WHERE source_id=?',(source_id,))
    records=c.execute('''SELECT id,external_id,content_type,name,structured_json FROM content_records
                         WHERE source_id=? AND source_version_id=? ORDER BY content_type,name,id''',(source_id,version_id)).fetchall()
    prefix='O5E-'+_slug(src['provider_document_key'] or source_id)
    total=0
    for row in records:
        ext=str(row['external_id'] or row['name'] or row['id'])
        stable=_slug(ext)
        digest=hashlib.sha1(f"{row['content_type']}:{ext}".encode()).hexdigest()[:8].upper()
        base=f"{prefix}-{_slug(row['content_type'])}-{stable}-{digest}"
        text=record_text(row['content_type'],row['name'] or ext,row['structured_json'])
        chunks=split_text(text)
        heading=f"{row['content_type'].replace('_',' ').title()} — {row['name'] or ext}"
        for idx,chunk in enumerate(chunks,1):
            eid=f"{base}-C{idx:02d}"
            c.execute('''INSERT INTO evidence_chunks(evidence_id,source_id,source_version_id,content_record_id,page_pdf,page_label,heading,text)
                         VALUES(?,?,?,?,NULL,?,?,?)''',(eid,source_id,version_id,row['id'],ext,heading,chunk))
            total+=1
    return total
