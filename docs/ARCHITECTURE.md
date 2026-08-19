# Architecture

## Runtime path

```text
Player / Pi
   |
   v
Archie skill or CLI
   |
   +--> verify pinned SRD SHA-256
   |
   +--> SQLite FTS5 retrieval over page-aware chunks
   |
   +--> evidence packet with immutable IDs
   |
   +--> local Gemma answer pass (JSON claims + citations)
   |
   +--> deterministic evidence-ID validation
   |
   +--> local Gemma evidence-only audit
   |
   +--> fail closed if any claim is unsupported
   v
Player-facing VERIFIED / DERIVED / PARTIAL / NOT_IN_SRD answer
```

## Why FTS5 in v1

D&D rules contain distinctive named terms, spells, features, conditions, and glossary vocabulary. SQLite FTS5 gives fast, inspectable, offline retrieval without requiring a second embedding model. The database can later add an embeddings table and reciprocal-rank fusion while preserving identical evidence IDs and authority policy.

## Evidence IDs

`SRD521-P###-C##` identifies a chunk extracted from a specific PDF page. IDs are generated deterministically during ingestion. Page boundaries are never crossed by a chunk.

## Trust layers

1. **Source integrity:** SHA-256 pin before ingestion and retrieval.
2. **Closed corpus:** no network retrieval path in the answer engine.
3. **Retrieval before generation:** answer model sees explicit local evidence.
4. **Citation binding:** generated claim IDs must be members of retrieved evidence IDs.
5. **Audit:** second model pass is told it knows nothing except supplied evidence.
6. **Fail closed:** audit uncertainty yields a cautious answer rather than guessed rules.
7. **Human inspectability:** CLI prints evidence IDs and PDF pages.

No layer alone guarantees correctness. Together they make unsupported rules claims substantially harder to emit silently.
