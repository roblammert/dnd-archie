from __future__ import annotations
import argparse, json, sys
from .source import verify_source
from .ingest import ingest
from .retrieve import search, diagnose
from .answer import ask
from .characters import load_character,list_characters
from .config import settings

def print_answer(r):
    print(f"[{r.status}]\n{r.answer}")
    if r.claims:
        print('\nEvidence-backed claims:')
        byid={e.evidence_id:e for e in r.evidence}
        for c in r.claims:
            refs=', '.join(f"{x} (PDF p.{byid[x].page_pdf})" for x in c['evidence_ids'])
            print(f"- {c['text']} [{c['kind']}] — {refs}")
    print(f"\nProvenance: {r.reason}")

def main(argv=None):
    p=argparse.ArgumentParser(prog='archie',description='SRD 5.2.1 evidence-gated D&D player assistant')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('verify-source')
    sub.add_parser('ingest')
    s=sub.add_parser('search'); s.add_argument('query'); s.add_argument('--top-k',type=int,default=None); s.add_argument('--json',action='store_true')
    d=sub.add_parser('diagnose-retrieval'); d.add_argument('query'); d.add_argument('--top-k',type=int,default=None)
    a=sub.add_parser('ask'); a.add_argument('question'); a.add_argument('--character'); a.add_argument('--no-audit',action='store_true')
    sub.add_parser('characters')
    sub.add_parser('doctor')
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
                    print(f"[{r.evidence_id}] {role} PDF p.{r.page_pdf} | {r.heading} | score={r.score:.3f}\n{r.text[:900]}\n---")
        elif args.cmd=='diagnose-retrieval':
            print(json.dumps(diagnose(args.query,args.top_k),indent=2))
        elif args.cmd=='ask':
            raw=None
            if args.character: _,_,raw=load_character(args.character)
            print_answer(ask(args.question,raw,strict_audit=not args.no_audit))
        elif args.cmd=='characters':
            for x in list_characters(): print(x.name)
        elif args.cmd=='doctor':
            src=verify_source()
            print('Source: OK',src['sha256'])
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
