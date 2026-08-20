# Archie Source Library

Each source lives in its own directory and has a `source.yaml` manifest. Source manifests define identity, authority, representation, edition, priority, licensing metadata, and the pinned content version/hash.

Archie v2.0.0-alpha.5.1 has one D&D content authority, Wizards of the Coast SRD 5.2.1 (`wotc:srd-5.2.1`), represented by four exact bindings:

| Source ID | Representation ID | State |
|---|---|---|
| `srd521` | `wotc:official-srd-5.2.1` | enabled/searchable |
| `open5e:srd-2024` | `open5e:srd-2024` | enabled/searchable |
| `foundry:srd-5.2` | `foundry:srd-5.2` | disabled/non-searchable |
| `cantilux:dnd-srd-json` | `cantilux:dnd-srd-json` | disabled/non-searchable |

Third-party providers supply machine-readable representations; they are not independent rules authorities. Importers validate provider-specific provenance and pinned revisions before admission. The authoritative declaration is `sources/wotc-srd-5.2.1.yaml`.
