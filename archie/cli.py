from __future__ import annotations
import argparse, json, sys
from .source import verify_source
from .source_library import list_sources, show_source, verify_sources
from .ingest import ingest
from .retrieve import search, diagnose
from .answer import ask
from .characters import load_character,list_characters
from .config import settings
from .open5e import discover_open5e, inventory_from_snapshot


def print_answer(r):
    print(f"[{r.status}]\n{r.answer}")
    if r.claims:
        print('\nEvidence-backed claims:')
        byid={e.evidence_id:e for e in r.evidence}
        for c in r.claims:
            refs=', '.join(f"{x} (PDF p.{byid[x].page_pdf})" for x in c['evidence_ids'])
            print(f"- {c['text']} [{c['kind']}] — {refs}")
    print(f"\nProvenance: {r.reason}")


def _print_sources(rows):
    print(f"{'ID':<12} {'TYPE':<16} {'AUTHORITY':<20} {'EDITION':<9} {'ENABLED':<8} {'VERSION':<10} CHUNKS")
    for x in rows:
        print(f"{x['id']:<12} {x['source_type']:<16} {x['authority_type']:<20} {(x['edition'] or '-'):<9} "
              f"{('yes' if x['enabled'] else 'no'):<8} {(x['version'] or '-'):<10} {x['evidence_chunks']}")


def _short_meta(value):
    if isinstance(value, dict):
        return str(value.get('name') or value.get('key') or value.get('title') or '-')
    return str(value or '-')


def main(argv=None):
    p=argparse.ArgumentParser(prog='archie',description='Evidence-gated D&D player assistant')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('verify-source')
    sub.add_parser('ingest')
    s=sub.add_parser('search'); s.add_argument('query'); s.add_argument('--top-k',type=int,default=None); s.add_argument('--json',action='store_true')
    d=sub.add_parser('diagnose-retrieval'); d.add_argument('query'); d.add_argument('--top-k',type=int,default=None)
    a=sub.add_parser('ask'); a.add_argument('question'); a.add_argument('--character'); a.add_argument('--no-audit',action='store_true')
    sub.add_parser('characters')
    sub.add_parser('doctor')

    src=sub.add_parser('sources',help='Inspect and verify the local Source Library')
    srcsub=src.add_subparsers(dest='sources_cmd',required=True)
    sl=srcsub.add_parser('list'); sl.add_argument('--json',action='store_true')
    ss=srcsub.add_parser('show'); ss.add_argument('source_id'); ss.add_argument('--json',action='store_true')
    sv=srcsub.add_parser('verify'); sv.add_argument('--json',action='store_true')
    sd=srcsub.add_parser('discover',help='Discover external source-provider catalogs without importing content')
    sd.add_argument('provider',choices=['open5e']); sd.add_argument('--json',action='store_true')
    si=srcsub.add_parser('inventory',help='Inspect the latest external discovery snapshot')
    si.add_argument('provider',choices=['open5e']); si.add_argument('--document'); si.add_argument('--json',action='store_true')

    args=p.parse_args(argv)
    try:
        if args.cmd=='verify-source': print(json.dumps(verify_source(),indent=2))
        elif args.cmd=='ingest': print(json.dumps(ingest(),indent=2))
        elif args.cmd=='search':
            rows=search(args.query,args.top_k)
            if args.json: print(json.dumps([r.to_dict() for r in rows],indent=2))
            else:
                for r in rows:
                    role='PRIMARY' if r.origin=='primary' else 'CONTEXT'
                    print(f"[{r.evidence_id}] {role} {r.source_id}/{r.authority_type}/{r.edition or '-'} PDF p.{r.page_pdf} | {r.heading} | score={r.score:.3f}\n{r.text[:900]}\n---")
        elif args.cmd=='diagnose-retrieval':
            print(json.dumps(diagnose(args.query,args.top_k),indent=2))
        elif args.cmd=='ask':
            raw=None
            if args.character: _,_,raw=load_character(args.character)
            print_answer(ask(args.question,raw,strict_audit=not args.no_audit))
        elif args.cmd=='characters':
            for x in list_characters(): print(x.name)
        elif args.cmd=='sources':
            if args.sources_cmd=='list':
                rows=list_sources()
                print(json.dumps(rows,indent=2) if args.json else '',end='') if args.json else _print_sources(rows)
            elif args.sources_cmd=='show':
                x=show_source(args.source_id)
                if args.json: print(json.dumps(x,indent=2))
                else:
                    print(f"Source: {x['name']}\nID: {x['id']}\nType: {x['source_type']}\nAuthority: {x['authority_type']}\nEdition: {x['edition'] or '-'}\nEnabled: {'yes' if x['enabled'] else 'no'}\nPriority: {x['priority']}\nVersion: {x['version']}\nSHA-256: {x['sha256']}\nContent records: {x['content_records']}\nEvidence chunks: {x['evidence_chunks']}\nStatus: VERIFIED")
            elif args.sources_cmd=='verify':
                x=verify_sources()
                if args.json: print(json.dumps(x,indent=2))
                else:
                    for item in x['sources']:
                        print(f"OK {item['source_id']} {item['version']} {item['sha256']}")
                    print(f"Verified {x['enabled_count']} enabled source(s).")
            elif args.sources_cmd=='discover':
                x=discover_open5e()
                if args.json: print(json.dumps(x,indent=2))
                else:
                    print(f"Open5e V2 discovery complete: {x['document_count']} document(s)")
                    print(f"Snapshot: {x['snapshot_path']}")
                    print(f"SHA-256: {x['snapshot_sha256']}")
                    print('No Open5e content was imported into Archie.')
            elif args.sources_cmd=='inventory':
                x=inventory_from_snapshot(args.document)
                if args.json: print(json.dumps(x,indent=2))
                else:
                    print(f"Open5e V2 inventory snapshot: {x['generated_at']}")
                    for d in x['documents']:
                        counts=d.get('resource_counts',{})
                        total=sum(v for v in counts.values() if isinstance(v,int))
                        print(f"{d['key']}: {d['name']} | resources={total} | license={_short_meta(d.get('license'))}")
                        print('  '+', '.join(f"{k}={v if v is not None else '?'}" for k,v in counts.items()))
                    print('Inventory only; no Open5e content is enabled or searchable by Archie.')
        elif args.cmd=='doctor':
            srcinfo=verify_source()
            print('Source: OK',srcinfo['sha256'])
            print('Source ID:',srcinfo['source_id'])
            print('Authority:',srcinfo['authority_type'])
            print('Edition:',srcinfo['edition'])
            print('Index:', 'present' if settings.database.exists() else 'missing (run ingest)')
            print('LLM endpoint:',settings.llm_base_url)
            print('LLM model:',settings.llm_model)
            print('Strict audit:',settings.strict_audit)
            print('Top K:',settings.top_k)
            print('Neighbor radius:',settings.neighbor_radius)
    except Exception as e:
        print(f"ERROR: {e}",file=sys.stderr); return 2
    return 0

if __name__=='__main__': raise SystemExit(main())
