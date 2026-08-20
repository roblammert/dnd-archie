# Archie v2.0.0-alpha.5.1

- Package: `2.0.0a5.post1`
- Base: `v2.0.0-alpha.5`
- Purpose: WotC SRD 5.2.1 multi-representation ingestion bridge before alpha.6.
- Sole authority: `wotc:srd-5.2.1`

Validated source inventory:

| Source | Representation | State |
|---|---|---|
| `srd521` | `wotc:official-srd-5.2.1` | searchable |
| `open5e:srd-2024` | `open5e:srd-2024` | searchable |
| `foundry:srd-5.2` | `foundry:srd-5.2` | disabled/non-searchable |
| `cantilux:dnd-srd-json` | `cantilux:dnd-srd-json` | disabled/non-searchable |

Final cross-representation authority selection, deduplication, conflict resolution, retrieval hardening, and answer minimization remain intentionally deferred to alpha.6.
