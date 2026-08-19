# Archie v2.0.0-alpha.3

Archie is a local, evidence-gated D&D player assistant. v2.0.0-alpha.3 adds **selective Open5e V2 import and immutable local snapshots** on top of the Source Library foundation while preserving the frozen v1.6 trust engine.

The only enabled/searchable rules authority remains the locally pinned **System Reference Document 5.2.1** (`srd521`). Open5e `srd-2024` may be imported as structured local content, but alpha.3 always stores it as **approved=no / enabled=no** and creates **zero evidence chunks**.

## Bootstrap

```bash
./scripts/bootstrap.sh
source .venv/bin/activate
python -m archie.cli doctor
```

## Source Library

```bash
python -m archie.cli sources list
python -m archie.cli sources show srd521
python -m archie.cli sources verify
```

## Open5e discovery

```bash
python -m archie.cli sources discover open5e
python -m archie.cli sources inventory open5e --document srd-2024
./scripts/run_open5e_discovery.sh
```

## Selective Open5e import

Alpha.3 intentionally allows only `srd-2024`.

```bash
python -m archie.cli sources import open5e srd-2024
python -m archie.cli sources show open5e:srd-2024
python -m archie.cli sources list
```

Import stores:

- the original Open5e JSON document/resource payload under `sources/open5e/srd-2024/raw/`;
- a SHA-256 content identity and source version;
- normalized structured records in SQLite;
- a local `source.yaml` manifest;
- explicit `approved: false`, `enabled: false`, and license status.

**Import does not grant rules authority.** Alpha.3 creates no Open5e evidence chunks and Retrieval v2 continues to search only enabled evidence sources. Missing license metadata blocks automatic approval/enabling.

For a shareable live import report:

```bash
./scripts/run_open5e_import.sh
```

This writes `open5e-import-results.md`.

## Retrieval and answers

```bash
python -m archie.cli search "advantage"
python -m archie.cli diagnose-retrieval "What does Prone do?"
python -m archie.cli ask "What happens when I have Advantage?"
```

## Release checks

```bash
./scripts/release_check.sh
./scripts/run_regression.sh
./scripts/run_epistemic_regression.sh
```

Alpha.4 is reserved for explicit source approval and multi-source trust-engine behavior. No Open5e content can answer a player question in alpha.3.
