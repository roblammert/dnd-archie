# Changelog

## 1.0.0 — 2026-08-19

Initial release: pinned SRD 5.2.1 authority, page-aware ingestion, SQLite FTS5 retrieval, evidence-bound local-LLM answers, strict claim audit, character YAML storage, Pi project skills, and regression tests.

## 1.5.0 — Retrieval & Audit Hardening
- Added deterministic concept-aware Retrieval v2.
- Added multi-concept query decomposition and definition-oriented exact phrase boosting.
- Added child-language retrieval aliases without granting aliases rules authority.
- Added cross-page/document-order neighbor expansion.
- Added `archie retrieve-debug` diagnostics.
- Added full player-facing answer coverage to the strict evidence audit.
- Preserved llama.cpp JSON response enforcement and disabled extended thinking.
- Added regression coverage for prior failures: Prone, Restrained, Concentration, Help, Armor Class wording, Spell Save DC, Passive Perception, multi-concept comparison, Invisible false premise, and answer-audit escape.
