# Architecture — v2.0.0-alpha.6

## One authority, four representations

WotC SRD 5.2.1 (`wotc:srd-5.2.1`) is Archie's sole D&D rules authority. The official PDF, Open5e SRD-2024, Foundry SRD 5.2, and Cantilux dnd-srd-json are four auditable representations of that same authority. Provider agreement is not voting, and duplicate representations cannot amplify a score.

## Evidence path

```text
source observation
  -> deterministic taxonomy
  -> canonical entity mapping
  -> evidence family + allowlisted structured facts
  -> searchable eligibility
  -> SQLite FTS candidate
  -> family aggregation
  -> entity budgeting
  -> field/evidence-kind member selection
  -> conflict gate
  -> evidence packet, generation, and audit
  -> answer
```

A family represents one comparable claim and scope. Family ranking uses the best eligible member score, not a sum across providers. Retrieval budgets families and entities before selecting the most suitable evidence member. Structured facts are field-specific; a conflict blocks the affected family/claim while unrelated clear fields on the same entity remain usable.

## Identity and fallback

Structured observations map only when deterministic evidence identifies a canonical SRD entity. Ambiguous observations are quarantined; leaving an observation unmapped is safer than creating a false merge. Deterministic synthetic families allow otherwise eligible unmapped evidence to remain isolated instead of being blended.

The official PDF is page-oriented. PDF pages remain authoritative evidence containers and retrieval fallback without being forced into canonical structured-entity mappings.

## Trust boundary

Pinned artifacts and importer-specific provenance checks establish representation identity. Search eligibility requires approved, licensed, enabled, active-edition evidence that passes identity and quarantine policy. Conflicted families fail closed; representations never vote. Only evidence cited by answer claims appears in provenance, rendered to players as the single `SRD 5.2.1` authority.

Retrieval and rules logic live in the Archie core answer service shared by CLI and Pi. Local model generation is followed by deterministic evidence-ID validation and an evidence-only audit; uncertainty remains fail-closed under the v1.6 epistemic contract.
