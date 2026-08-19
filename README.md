# Archie v2.0.0-alpha.2

Archie is a local, evidence-gated D&D player assistant. v2.0.0-alpha.2 adds **Open5e V2 discovery and inventory** on top of the alpha.1 Source Library foundation while preserving the frozen v1.6 trust engine.

The only enabled/searchable rules authority remains the locally pinned **System Reference Document 5.2.1**. Open5e data discovered in this alpha is metadata only and is never sent to Gemma as rules evidence.

## Bootstrap

```bash
./scripts/bootstrap.sh
source .venv/bin/activate
python -m archie.cli doctor
```

## Local Source Library

```bash
python -m archie.cli sources list
python -m archie.cli sources show srd521
python -m archie.cli sources verify
```

## Open5e V2 discovery

Discovery is an explicit network operation. It inventories the Open5e document catalog and resource counts, then stores a local hashable snapshot.

```bash
python -m archie.cli sources discover open5e
python -m archie.cli sources inventory open5e
python -m archie.cli sources inventory open5e --document srd-2024
```

For machine-readable output:

```bash
python -m archie.cli sources discover open5e --json
python -m archie.cli sources inventory open5e --json
```

`inventory` reads the latest local snapshot and does not contact Open5e.

For a shareable live inventory report:

```bash
./scripts/run_open5e_discovery.sh
```

This writes `open5e-discovery-results.md`.

**Alpha.2 does not import, enable, index, retrieve, or answer from Open5e content.** Source approval/import is reserved for alpha.3.

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

See `docs/SOURCE_LIBRARY_ALPHA1.md` and `docs/OPEN5E_DISCOVERY_ALPHA2.md` for the architecture and trust boundaries.
