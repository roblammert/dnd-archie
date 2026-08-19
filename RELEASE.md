# Archie v2.0.0-alpha.1

**Stage:** Source Library Foundation

This alpha migrates the frozen v1.6 trust engine onto a generic local Source Library without adding any new D&D rules authority.

## Included

- generic multi-source SQLite schema;
- explicit source/version/authority/edition metadata;
- SRD 5.2.1 registered as `srd521` / `official_srd` / `2024`;
- preserved `SRD521-P...` evidence IDs;
- new `archie sources list|show|verify` CLI;
- rebuild-from-source index migration;
- source metadata on retrieval results.

## Intentionally excluded

Open5e, 2014 fallback, house-rule precedence, source conflict resolution, and all web application code.

The alpha.1 acceptance criterion is behavioral parity with the v1.6 trust engine while the storage/retrieval layer becomes source-aware.
