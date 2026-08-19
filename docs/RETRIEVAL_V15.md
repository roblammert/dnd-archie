# Retrieval v2 — Archie 1.5

Archie 1.5 improves recall while keeping the SRD authority boundary deterministic.

## Query planning

A player question is normalized into content terms, recognized canonical concepts, child-language aliases, and exact concept subqueries. Aliases are search hints only and never become evidence.

## Candidate retrieval

SQLite FTS5 retrieves a broad candidate pool. Exact canonical subqueries are also executed independently. BM25 is then augmented with deterministic bonuses for exact concept presence, known definition markers such as `Prone [Condition]`, and appropriate SRD top-level sections.

## Multi-concept coverage

For questions containing multiple concepts, one strong exact hit is reserved for each concept before remaining slots are filled globally. This prevents comparison questions such as ability check vs saving throw from retrieving only one side.

## Neighbor expansion

The strongest primary hits are expanded by document-order neighbors. Expansion may cross PDF page boundaries, solving cases where a rule heading is at the end of one page and its mechanics continue on the next page.

## Diagnostics

Use:

```bash
python -m archie.cli diagnose-retrieval "<question>"
```

The output shows terms, aliases, concepts, subqueries, scores, primary hits, and context chunks.

## Trust boundary

Retrieval logic may decide **where to look**. Only retrieved SRD text may decide **what the rule is**.
