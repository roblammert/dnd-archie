# Changelog

## 1.5.1 — Reliability patch

- Added one bounded model-contract correction retry for malformed answer structures.
- Normalizes harmless status/kind casing and whitespace without inventing evidence.
- Malformed answer/audit JSON now fails closed as PARTIAL instead of crashing the CLI.
- Strengthened audit coverage with clause-level `answer_units`; every factual answer clause must be certified.
- Added explicit guards against inferring permission from penalties/restrictions.
- Added explicit separation of targeting, attack rolls, visibility, and sight-required effects.
- Added permanent regression fixtures for spell-save DC, Long Rest, Prone/longbow permission, and Invisible targeting.
- No authority expansion: SRD 5.2.1 remains the sole D&D rules source.

## 1.5.0 — 2026-08-19

Reliability and retrieval release based on the v1.1 live regression run.

### Retrieval v2
- Added deterministic concept-aware retrieval without using the LLM to invent search facts.
- Added stronger stop-word filtering for natural-language questions.
- Added exact canonical concept searches and section/definition boosting.
- Added multi-concept reservation so comparison questions retrieve evidence for both sides.
- Added cross-page, document-order neighbor expansion around strong primary hits.
- Added child-language query aliases such as `armor number -> armor class` and `sneak -> hide/stealth`.
- Added `diagnose-retrieval` for inspectable query plans and evidence selection.

### Evidence/audit hardening
- Strict audit now inspects the player-facing answer as well as `claims[]`.
- Added `answer_fully_covered` gate to catch unsupported mechanics omitted from structured claims.
- Preserved fail-closed behavior for unsupported or incomplete answers.
- Tightened answer scope and claim minimality for beginner-facing responses.

### Runtime and packaging carried forward from v1.1
- `.env` loading via `python-dotenv` with shell variables taking precedence.
- Explicit setuptools package discovery to avoid flat-layout editable-install failures.
- Migrated deprecated `fitz` import to `pymupdf`.
- Added llama.cpp JSON response formatting, capped output tokens, and disabled model thinking.
- Default retrieval `top_k` reduced to 6 with a larger internal candidate pool.

### Validation
- Added v1.5 evidence-coverage tests for regression failures including Prone, Concentration, spell save DC, Passive Perception, Help, Restrained, Invisible, comparisons, and jumping.
- Added deterministic child-language alias and neighbor-expansion tests.

## 1.0.0 — 2026-08-19

Initial release: pinned SRD 5.2.1 authority, page-aware ingestion, SQLite FTS5 retrieval, evidence-bound local-LLM answers, strict claim audit, character YAML storage, Pi project skills, and regression tests.
