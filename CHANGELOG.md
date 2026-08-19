# Changelog

## 2.0.0-alpha.2 — Open5e Discovery and Inventory

- Added an Open5e V2 client used only by explicit source-discovery commands.
- Added `archie sources discover open5e` to enumerate Open5e source documents and resource counts.
- Added `archie sources inventory open5e` for offline inspection of the latest local discovery snapshot.
- Captures document key/name, publisher, per-document license metadata, game system, author, publication date, permalink, and resource counts where supplied.
- Inventories classes, subclasses, species, spells, backgrounds, feats, equipment/items, magic items, rules, conditions, and creatures without downloading full content records.
- Uses Open5e V2 `document__key__in` filtering and result counts to minimize transferred data.
- Stores timestamped discovery snapshots plus `latest.json`, with a deterministic SHA-256 over normalized snapshot data.
- Adds Open5e base URL and timeout configuration.
- Explicitly separates Open5e software licensing from each discovered content document's license metadata.
- No Open5e document is registered, enabled, indexed, searchable, or available to the LLM in alpha.2.
- No web application code is included.

## 2.0.0-alpha.1 — Source Library Foundation

- Generalized the SQLite corpus into `sources`, `source_versions`, `content_records`, `evidence_chunks`, and FTS.
- Registered SRD 5.2.1 as source `srd521` with explicit `official_srd` authority and `2024` edition metadata.
- Preserved existing SRD evidence IDs and v1.6 trust behavior.
- Added source metadata to every retrieved `Evidence` object.
- Added `archie sources list`, `archie sources show`, and `archie sources verify`.
- Moved the pinned SRD manifest to `sources/srd521/source.yaml`.
- Index ingestion now rebuilds generated SQLite storage from scratch under the current schema.
- No Open5e integration or web code is included in this alpha.

## 1.6.0rc1 — Auditor repair observability release candidate

- Replaced the dev.4 audit retry with a compact repair-specific system contract.
- The repair request explicitly enumerates required premise and claim indexes.
- A successful structured-output repair is recorded in provenance as `Audit structured-output correction succeeded.`
- Exhausted repair now reports both the malformed initial audit and malformed correction retry.
- Transport/server failures still remain operational errors and are never converted into rules uncertainty.
- No changes to Retrieval v2, SRD authority, premise guards, permission guards, or the 38+7 live suites.

## 1.6.0.dev4 — Release-candidate permission/auditor hardening

- Extended deterministic unresolved-premise guarding to direct Prone + bow/longbow permission questions, including `Can I`, `May I`, `Am I allowed`, `Is it allowed/legal`, and `While Prone, can I` forms.
- Kept the permission guard narrow so directly answerable `Can I` questions continue through normal SRD evidence evaluation.
- Added one bounded correction retry when the evidence auditor returns malformed structured output.
- A second malformed audit still fails closed as `PARTIAL`; transport/server failures remain operational errors.
- Added deterministic dev.4 tests for unresolved, positively answerable, and negatively answerable permission questions plus auditor retry/fail-closed behavior.
- Existing 38-question baseline and 7-question epistemic live suites remain unchanged.
- Retrieval v2 and SRD 5.2.1 sole-authority contract are unchanged.

## 1.6.0.dev3 — Premise-state enforcement

- Added deterministic `forced_unresolved_premise()` guards for broad inference families that narrower evidence must not settle.
- Invisible targeting and Invisible automatic-miss propositions are forced to `UNRESOLVED` unless a future evidence path explicitly proves the broader proposition.
- Prone/bow permission inference is likewise guarded from being inferred merely from an attack-roll penalty.
- Forced unresolved state is applied in Python before contract validation, so invalid or overconfident model status values cannot bypass the guard.
- Claims that directly resolve a forced-unresolved proposition are removed before the player-facing answer is canonicalized.
- The unresolved renderer states only the unresolved proposition and independently supported SRD claims.
- Added deterministic dev.3 regression tests for targeting, automatic misses, permission inference, invalid model statuses, and claim filtering.
- Existing 38-question and 7-question live regression suites remain unchanged.
- SRD 5.2.1 remains the sole D&D rules authority.

## 1.6.0.dev2 — Premise classification hardening

- Narrowed premise detection so ordinary yes/no questions and character/calculation inputs do not become material premises.
- Added deterministic absence-of-evidence inference detection.
- Canonicalized unresolved player-facing answers to neutral language after generation.
- Restored v1.5.1 baseline behavior for Passive Perception, Advantage stacking, and Heroic Inspiration interactions.
- Added premise-hardening regression tests.

## 1.6.0.dev1 — Epistemic premise classification

- Added explicit material-premise states: `SUPPORTED`, `CONTRADICTED`, and `UNRESOLVED`.
- `SUPPORTED` and `CONTRADICTED` premises require exact SRD evidence IDs; `UNRESOLVED` premises may not claim evidentiary support.
- An answer with an unresolved material premise cannot be marked `VERIFIED` or `DERIVED`.
- Strict audit now checks that every material proposition asserted or presupposed by the player's question is classified.
- Added a non-entailment rule: absence of evidence for X never establishes not-X, and absence of evidence for not-X never establishes X.
- Added explicit protection against using attack, visibility, sight-required effects, or penalties to settle broader targeting/permission propositions.
- Strict audit now runs for all generated responses with retrieved evidence, including claim-free `PARTIAL`/`NOT_IN_SRD` responses.
- Added v1.6 epistemic regression tests while preserving the v1.5.1 contracts and 38-question compatibility suite.
- SRD 5.2.1 remains the sole D&D rules authority.


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
