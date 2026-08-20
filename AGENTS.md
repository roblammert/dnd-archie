# Archie Agent Contract — v2.0.0-alpha.5.1

Archie is an evidence-gated D&D player assistant. Gemma pretrained D&D knowledge is never a rules authority.

## Authority rules

1. Only approved, licensed, enabled sources in the active edition may enter retrieval.
2. `official_srd` outranks `approved_supplement` on overlap.
3. Supplemental-only answers are permitted only when their cited approved evidence establishes the requested claim.
4. Retrieved-but-uncited sources must not appear in answer provenance.
5. Conflicting same-entity structured records must fail closed; never blend them into a hybrid rule.
6. Exact duplicate evidence should be suppressed before generation, preserving the higher-ranked authority.
7. Character data is factual input about a character, never rules authority.
8. House rules and 2014 fallback are not enabled in alpha.5.
9. The v1.6 epistemic/non-entailment and audit fail-closed behavior remains mandatory.

## Source contract

1. Wizards of the Coast SRD 5.2.1 is the sole current D&D content authority, identified as `wotc:srd-5.2.1`.
2. Authority identity and machine-readable representation identity are distinct. The permitted exact source-to-representation bindings are `srd521` → `wotc:official-srd-5.2.1`, `open5e:srd-2024` → `open5e:srd-2024`, `foundry:srd-5.2` → `foundry:srd-5.2`, and `cantilux:dnd-srd-json` → `cantilux:dnd-srd-json`.
3. `source_id` and `authority_type` retain their legacy compatibility meanings; neither replaces `authority_id` or `representation_id`.
4. Open5e retains its alpha.5 retrieval participation. Foundry and Cantilux are normalized but remain quarantined from evidence, FTS, and retrieval until alpha.6.
5. Importer-specific provenance validation is mandatory even when a record declares the valid authority ID.
6. Deterministic pinned artifacts are the rebuild inputs.
7. Final cross-representation authority selection, deduplication, conflict resolution, and retrieval policy remain alpha.6 work.

## Frontend rule

CLI and future web interfaces must consume the same Archie core answer service. Do not place retrieval or rules logic in frontend code.
