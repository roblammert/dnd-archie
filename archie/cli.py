from __future__ import annotations

import argparse
import json
import sys

from .answer import ask
from .characters import list_characters, load_character
from .config import settings
from .ingest import ingest
from .retrieve import retrieval_debug, search
from .source import verify_source


def print_answer(result):
    print(f"[{result.status}]\n{result.answer}")
    if result.claims:
        print("\nEvidence-backed claims:")
        byid = {e.evidence_id: e for e in result.evidence}
        for claim in result.claims:
            refs = ", ".join(
                f"{eid} (PDF p.{byid[eid].page_pdf})" for eid in claim["evidence_ids"]
            )
            print(f"- {claim['text']} [{claim['kind']}] — {refs}")
    print(f"\nProvenance: {result.reason}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="archie", description="SRD 5.2.1 evidence-gated D&D player assistant"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify-source")
    sub.add_parser("ingest")

    search_parser = sub.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--top-k", type=int, default=8)
    search_parser.add_argument("--json", action="store_true")

    debug_parser = sub.add_parser("retrieve-debug")
    debug_parser.add_argument("query")
    debug_parser.add_argument("--top-k", type=int)

    ask_parser = sub.add_parser("ask")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--character")
    ask_parser.add_argument("--no-audit", action="store_true")

    sub.add_parser("characters")
    sub.add_parser("doctor")
    args = parser.parse_args(argv)

    try:
        if args.cmd == "verify-source":
            print(json.dumps(verify_source(), indent=2))
        elif args.cmd == "ingest":
            print(json.dumps(ingest(), indent=2))
        elif args.cmd == "search":
            rows = search(args.query, args.top_k)
            if args.json:
                print(json.dumps([r.to_dict() for r in rows], indent=2))
            else:
                for row in rows:
                    print(
                        f"[{row.evidence_id}] PDF p.{row.page_pdf} | {row.heading} | {row.role}\n"
                        f"{row.text[:900]}\n---"
                    )
        elif args.cmd == "retrieve-debug":
            print(json.dumps(retrieval_debug(args.query, args.top_k), indent=2))
        elif args.cmd == "ask":
            raw = None
            if args.character:
                _, _, raw = load_character(args.character)
            print_answer(ask(args.question, raw, strict_audit=not args.no_audit))
        elif args.cmd == "characters":
            for item in list_characters():
                print(item.name)
        elif args.cmd == "doctor":
            src = verify_source()
            print("Source: OK", src["sha256"])
            print("Index:", "present" if settings.database.exists() else "missing (run ingest)")
            print("LLM endpoint:", settings.llm_base_url)
            print("LLM model:", settings.llm_model)
            print("Strict audit:", settings.strict_audit)
            print("Retrieval: v2 (concept + BM25 + neighbor expansion)")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
