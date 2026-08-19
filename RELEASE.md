# Archie v2.0.0-alpha.2

**Stage:** Open5e Discovery and Inventory

This alpha adds a read-only discovery boundary between Archie's local Source Library and the Open5e V2 API. It intentionally does **not** import Open5e game content into the trust engine.

## Included

- explicit Open5e V2 client;
- live `/v2/documents` source discovery;
- per-document inventory counts for player and GM resource categories;
- publisher/license/game-system/author/permalink provenance capture;
- local timestamped discovery snapshots plus `latest.json`;
- snapshot SHA-256;
- `archie sources discover open5e`;
- `archie sources inventory open5e [--document KEY]`;
- deterministic tests using a mocked Open5e API;
- all alpha.1 Source Library and v1.6 trust behavior preserved.

## Intentionally excluded

- Open5e content import;
- approval/enabling of Open5e documents;
- Open5e evidence chunks or retrieval;
- cross-source authority precedence;
- source conflict resolution;
- 2014 fallback behavior;
- house-rule precedence;
- web application code.

Alpha.2's acceptance criterion is that Archie can tell us **what Open5e offers and under what source/license metadata without learning any new rule from it.**
