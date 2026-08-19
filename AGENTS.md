# Archie Agent Contract — v2.0.0-alpha.5

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

## Frontend rule

CLI and future web interfaces must consume the same Archie core answer service. Do not place retrieval or rules logic in frontend code.
