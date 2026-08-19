# Archie v2.0.0-alpha.3

**Stage:** Open5e Selective Import & Snapshot System

Alpha.3 crosses the boundary from discovery to **local possession**, but not from possession to **authority**.

## Included

- selective Open5e V2 import, restricted to `srd-2024`;
- immutable raw JSON snapshots and SHA-256 content identities;
- normalized `content_records` for Open5e classes, subclasses, species, spells, backgrounds, feats, equipment, magic items, rules, conditions, and creatures;
- explicit imported/approved/enabled separation;
- missing-license visibility and automatic-approval block;
- disabled `open5e:srd-2024` source manifest and version metadata;
- idempotent same-content re-import;
- restoration of persistent imported records after SQLite rebuild;
- zero Open5e evidence chunks and zero Open5e answer retrieval;
- all prior trust-engine and discovery behavior preserved.

## Intentionally excluded

- enabling or approving Open5e sources;
- Open5e evidence generation;
- multi-source retrieval/answering;
- source precedence/conflict resolution;
- 2014 fallback;
- house-rule precedence;
- web application code.

Alpha.3 acceptance criterion: Archie may store and inspect `srd-2024` locally without gaining any new answer authority from it.
