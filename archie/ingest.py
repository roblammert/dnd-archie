from __future__ import annotations
import re, json
import pymupdf
from .config import settings
from .db import connect, initialize
from .source import verify_source, load_manifest

MAX_CHARS=1800
OVERLAP_PARAGRAPHS=1

# Page labels in the SRD largely track printed page numbers; PDF page count can include front matter.
def clean_page_text(raw: str) -> str:
    raw=raw.replace('\u00ad','').replace('\r','\n')
    lines=[]
    for line in raw.splitlines():
        line=re.sub(r'\s+',' ',line).strip()
        if not line: lines.append(''); continue
        # Drop isolated page-number/footer artifacts but preserve numeric rules text.
        if re.fullmatch(r'\d{1,3}', line): continue
        lines.append(line)
    text='\n'.join(lines)
    # Rejoin words hyphenated only because of PDF line wrapping.
    text=re.sub(r'([A-Za-z])-[\n ]+([a-z])', r'\1\2', text)
    text=re.sub(r'\n{3,}','\n\n',text)
    return text.strip()

def section_for_page(page: int) -> str:
    # Top-level section boundaries are taken from the SRD 5.2.1 table of contents.
    sections=[
      (1, "Legal / Contents"),
      (5, "Playing the Game"),
      (19, "Character Creation"),
      (28, "Classes"),
      (83, "Character Origins"),
      (87, "Feats"),
      (89, "Equipment"),
      (104, "Spells"),
      (176, "Rules Glossary"),
      (192, "Gameplay Toolbox"),
      (204, "Magic Items"),
      (254, "Monsters"),
      (343, "Animals"),
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
        # If a giant paragraph slipped through, split on sentence-ish boundaries.
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
    integrity=verify_source(); manifest=load_manifest()
    doc=pymupdf.open(settings.source_pdf)
    c=connect(); initialize(c)
    with c:
        c.execute('DELETE FROM chunks')
        c.execute('DELETE FROM metadata')
        total=0
        for pno,page in enumerate(doc, start=1):
            txt=clean_page_text(page.get_text('text'))
            if not txt: continue
            heading=section_for_page(pno)
            for n,chunk in enumerate(split_page(txt),start=1):
                eid=f"SRD521-P{pno:03d}-C{n:02d}"
                c.execute('INSERT INTO chunks(evidence_id,page_pdf,page_label,heading,text) VALUES(?,?,?,?,?)',
                          (eid,pno,str(pno),heading,chunk))
                total+=1
        meta={
          'authority_id':manifest['authority_id'],
          'source_sha256':integrity['sha256'],
          'source_filename':manifest['filename'],
          'pages':str(len(doc)),
          'chunks':str(total),
          'schema_version':'1'
        }
        c.executemany('INSERT INTO metadata(key,value) VALUES(?,?)',meta.items())
    c.close(); doc.close()
    return {'ok':True,**meta}
