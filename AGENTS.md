# Archie Agent Contract — v2.0.0-alpha.6

Archie is an evidence-gated D&D player assistant. Gemma pretrained D&D knowledge is never a rules authority.

## Authority rules

1. Only approved, licensed, enabled representations in the active edition may enter retrieval. WotC SRD 5.2.1 (`wotc:srd-5.2.1`) is the sole rules authority.
2. Representation identity is not authority identity. Provider agreement is never a vote and equivalent representations must not amplify a claim.
3. Structured observations may map deterministically to canonical entities. Unmapped is safer than a false merge; ambiguous identity evidence is quarantined.
4. An evidence family represents one comparable claim and scope. Its score is its best eligible member score, never the sum of member scores.
5. Structured facts are field-specific and allowlisted. Conflicted families fail closed, while unrelated clear fields remain usable.
6. PDF pages remain evidence containers rather than canonical entities.
7. Retrieved-but-uncited sources must not appear in provenance. Player-facing provenance renders the single SRD 5.2.1 authority.
8. Character data is factual input about a character, never rules authority. House rules and 2014 fallback are not enabled.
9. Every new D&D rules-fact question in Pi requires fresh Archie retrieval, even when the fact appeared earlier in the conversation.
10. The v1.6 epistemic/non-entailment and audit fail-closed behavior remains mandatory.

## Source contract

1. Wizards of the Coast SRD 5.2.1 is the sole current D&D content authority, identified as `wotc:srd-5.2.1`.
2. Authority identity and machine-readable representation identity are distinct. The permitted exact source-to-representation bindings are `srd521` → `wotc:official-srd-5.2.1`, `open5e:srd-2024` → `open5e:srd-2024`, `foundry:srd-5.2` → `foundry:srd-5.2`, and `cantilux:dnd-srd-json` → `cantilux:dnd-srd-json`.
3. `source_id` and `authority_type` retain their legacy compatibility meanings; neither replaces `authority_id` or `representation_id`.
4. All four representations are enabled in alpha.6. Searchable evidence is admitted by deterministic identity, family, fact, and quarantine policy.
5. Importer-specific provenance validation is mandatory even when a record declares the valid authority ID.
6. Deterministic pinned artifacts are the rebuild inputs.
7. Retrieval budgets evidence families and entities, selects eligible members by field and evidence kind, and fails closed at the conflicted claim/family scope.

## Frontend rule

CLI and future web interfaces must consume the same Archie core answer service. Do not place retrieval or rules logic in frontend code.
