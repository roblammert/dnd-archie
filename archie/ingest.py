from __future__ import annotations
import re, json
from datetime import datetime, timezone
import pymupdf
from .config import settings
from .db import rebuild_database, SCHEMA_VERSION
from .source import verify_source, get_source_manifest
from .open5e import rehydrate_open5e_imports
from .foundry import rehydrate_foundry_imports
from .cantilux import rehydrate_cantilux_imports

MAX_CHARS=1800
OVERLAP_PARAGRAPHS=1

def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def clean_page_text(raw: str) -> str:
    raw=raw.replace('\u00ad','').replace('\r','\n')
    lines=[]
    for line in raw.splitlines():
        line=re.sub(r'\s+',' ',line).strip()
        if not line: lines.append(''); continue
        if re.fullmatch(r'\d{1,3}', line): continue
        lines.append(line)
    text='\n'.join(lines)
    text=re.sub(r'([A-Za-z])-[\n ]+([a-z])', r'\1\2', text)
    text=re.sub(r'\n{3,}','\n\n',text)
    return text.strip()

def section_for_page(page: int) -> str:
    sections=[
      (1, "Legal / Contents"),(5, "Playing the Game"),(19, "Character Creation"),
      (28, "Classes"),(83, "Character Origins"),(87, "Feats"),(89, "Equipment"),
      (104, "Spells"),(176, "Rules Glossary"),(192, "Gameplay Toolbox"),
      (204, "Magic Items"),(254, "Monsters"),(343, "Animals"),
    ]
    current=sections[0][1]
    for start,name in sections:
        if page >= start: current=name
        else: break
    return current

def split_page(text: str):
    paras=[p.strip() for p in re.split(r'\n\s*\n',text) if p.strip()]
    if not paras: return []
    chunks=[]; cur=[]; size=0
    for p in paras:
        if cur and size+len(p)+2 > MAX_CHARS:
            chunks.append('\n\n'.join(cur))
            cur=cur[-OVERLAP_PARAGRAPHS:] if OVERLAP_PARAGRAPHS else []
            size=sum(len(x)+2 for x in cur)
        if len(p)>MAX_CHARS:
            bits=re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])',p)
            for b in bits:
                if cur and size+len(b)+1>MAX_CHARS:
                    chunks.append(' '.join(cur)); cur=[]; size=0
                cur.append(b); size += len(b)+1
        else:
            cur.append(p); size += len(p)+2
    if cur: chunks.append('\n\n'.join(cur))
    return [c.strip() for c in chunks if c.strip()]

def ingest() -> dict:
    integrity=verify_source()
    manifest=get_source_manifest(settings.source_id)
    doc=pymupdf.open(manifest.content_path)
    c=rebuild_database()
    now=_now()
    with c:
        c.execute('''INSERT INTO sources(id,name,source_type,authority_type,authority_id,representation_id,edition,enabled,approved,license_status,provider,provider_document_key,priority,
                     license_name,license_url,homepage_url,created_at,updated_at)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (manifest.id,manifest.name,manifest.source_type,manifest.authority_type,manifest.authority_id,manifest.representation_id,manifest.edition,
                   1 if manifest.enabled else 0,1 if manifest.approved else 0,manifest.license_status,manifest.provider,manifest.provider_document_key,
                   manifest.priority,manifest.license_name,manifest.license_url,manifest.homepage_url,now,now))
        cur=c.execute('''INSERT INTO source_versions(source_id,version,imported_at,content_sha256,source_uri,filename,upstream_revision,active)
                         VALUES(?,?,?,?,?,?,?,1)''',
                      (manifest.id,manifest.version,now,integrity['sha256'],manifest.source_uri,manifest.filename,manifest.upstream_revision))
        source_version_id=cur.lastrowid
        total=0; records=0
        for pno,page in enumerate(doc, start=1):
            txt=clean_page_text(page.get_text('text'))
            if not txt: continue
            heading=section_for_page(pno)
            structured=json.dumps({'page_pdf':pno,'page_label':str(pno),'section':heading},sort_keys=True)
            upstream_id=f'page:{pno}'
            cur=c.execute('''INSERT INTO content_records(source_id,source_version_id,external_id,content_type,name,edition,authority_id,representation_id,
                             upstream_id,upstream_path,normalization_schema_version,structured_json,created_at)
                             VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                          (manifest.id,source_version_id,upstream_id,'page',f'PDF page {pno}',manifest.edition,
                           manifest.authority_id,manifest.representation_id,upstream_id,f'{manifest.filename}#page={pno}',1,structured,now))
            record_id=cur.lastrowid; records+=1
            for n,chunk in enumerate(split_page(txt),start=1):
                eid=f"SRD521-P{pno:03d}-C{n:02d}"
                c.execute('''INSERT INTO evidence_chunks(evidence_id,source_id,source_version_id,content_record_id,page_pdf,page_label,heading,text)
                             VALUES(?,?,?,?,?,?,?,?)''',
                          (eid,manifest.id,source_version_id,record_id,pno,str(pno),heading,chunk))
                total+=1
        meta={
          'authority_id':manifest.id,
          'source_id':manifest.id,
          'source_sha256':integrity['sha256'],
          'source_filename':manifest.filename,
          'source_version':manifest.version,
          'pages':str(len(doc)),
          'content_records':str(records),
          'chunks':str(total),
          'schema_version':SCHEMA_VERSION,
        }
        c.executemany('INSERT INTO metadata(key,value) VALUES(?,?)',meta.items())
        restored=rehydrate_open5e_imports(c, now)
        restored_foundry=rehydrate_foundry_imports(c, now)
        restored_cantilux=rehydrate_cantilux_imports(c, now)
    c.close(); doc.close()
    return ({'ok':True,**meta,'restored_open5e_sources':restored['sources'],
             'restored_open5e_records':restored['content_records'],
             'restored_open5e_diagnostics':restored['diagnostics']}
            | {'restored_foundry_sources':restored_foundry['sources'],
               'restored_foundry_records':restored_foundry['content_records'],
               'restored_foundry_diagnostics':restored_foundry['diagnostics'],
               'restored_cantilux_sources':restored_cantilux['sources'],
               'restored_cantilux_records':restored_cantilux['content_records'],
               'restored_cantilux_diagnostics':restored_cantilux['diagnostics']})
