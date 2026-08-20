# Archie Source Library

Each source has a manifest defining source identity, authority, representation, edition, priority, licensing, and pinned artifact/revision.

Archie v2.0.0-alpha.6 has one D&D rules authority, WotC SRD 5.2.1 (`wotc:srd-5.2.1`), with four enabled representations:

| Source ID | Representation ID | Alpha.6 state |
|---|---|---|
| `srd521` | `wotc:official-srd-5.2.1` | enabled/searchable |
| `open5e:srd-2024` | `open5e:srd-2024` | enabled/searchable subject to quarantine |
| `foundry:srd-5.2` | `foundry:srd-5.2` | enabled/searchable subject to quarantine |
| `cantilux:dnd-srd-json` | `cantilux:dnd-srd-json` | enabled/searchable subject to quarantine |

Representation provenance remains independently auditable, but Open5e, Foundry, and Cantilux are not separate rules authorities and their agreement is never a vote. Importers validate provider-specific provenance and the unchanged pinned revisions before admission. The authority declaration is `sources/wotc-srd-5.2.1.yaml`.
