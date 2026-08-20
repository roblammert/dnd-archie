# Architecture — v2.0.0-alpha.5.1

## Authority and representations

The sole D&D content authority is WotC SRD 5.2.1 (`wotc:srd-5.2.1`). Authority answers who owns the rules content; representation identifies the pinned machine-readable form. The ingestion topology contains the official PDF, Open5e SRD-2024, Foundry SRD 5.2, and Cantilux dnd-srd-json representations.

Official and Open5e evidence retain alpha.5 retrieval behavior. Foundry and Cantilux records are normalized but quarantined from evidence, FTS, and retrieval until alpha.6. Exact source/representation bindings and importer-specific provenance checks prevent a valid authority label from bypassing admission.

Rebuilds start from pinned artifacts. A substantive corpus fingerprint excludes volatile timestamps and database row IDs so two rebuilds can be compared deterministically across all normalized records.

## Runtime path

```text
Player / Pi
   |
   v
Archie skill or CLI
   |
   +--> verify pinned source hashes and provenance
   |
   +--> Retrieval v2 query plan
   |      - normalize natural language
   |      - map search-only aliases
   |      - detect canonical concepts
   |      - reserve multi-concept coverage
   |
   +--> SQLite FTS5 candidate retrieval + deterministic re-ranking
   |
   +--> document-order neighbor expansion across page boundaries
   |
   +--> evidence packet with immutable IDs
   |
   +--> local Gemma answer pass (JSON claims + citations)
   |
   +--> deterministic evidence-ID validation
   |
   +--> local Gemma evidence-only audit of claims AND answer coverage
   |
   +--> fail closed if any claim or answer mechanic is unsupported
   v
Player-facing VERIFIED / DERIVED / PARTIAL / NOT_IN_SRD answer
```

## Why deterministic FTS5 remains the base

D&D rules contain distinctive named terms, conditions, actions, formulas, and glossary vocabulary. SQLite FTS5 is fast, inspectable, offline, and does not require an embedding model. v1.5 adds deterministic concept-aware ranking around FTS5 rather than delegating query rewriting to the LLM.

Embeddings may be added later as an additional recall channel, but they must never alter the authority boundary or evidence IDs.

## Evidence IDs

`SRD521-P###-C##` identifies a chunk extracted from one PDF page. IDs are deterministic during ingestion. Chunks remain page-bounded; retrieval may attach adjacent chunks in document order so a rule can continue naturally across a page boundary.

## Trust layers

1. **Source integrity:** SHA-256 pin before ingestion and retrieval.
2. **Closed corpus:** no network retrieval path in the answer engine.
3. **Deterministic retrieval planning:** aliases and concepts affect where Archie searches, never what it asserts.
4. **Retrieval before generation:** answer model sees explicit local evidence.
5. **Citation binding:** claim evidence IDs must exist in the supplied packet.
6. **Claim audit:** a second evidence-only pass validates each structured claim.
7. **Answer-coverage audit:** the auditor also checks that every factual mechanic in the player-facing answer is represented by supported claims.
8. **Fail closed:** audit uncertainty yields `PARTIAL` rather than guessed rules.
9. **Human inspectability:** CLI exposes evidence IDs, PDF pages, retrieval roles, and diagnostics.

No single layer guarantees correctness. The architecture is intentionally redundant so unsupported rules are difficult to emit silently.
