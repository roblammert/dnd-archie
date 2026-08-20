# Operations — v2.0.0-alpha.6

All release checks must run from the repository `.venv`:

```bash
source .venv/bin/activate
```

## Verify and rebuild

```bash
python -m archie.cli sources verify
python -m archie.cli ingest
python -m archie.cli sources list
```

The SQLite index is generated and disposable. Ingest rebuilds it from committed pinned artifacts. Alpha.6 expects all four representations—official, Open5e, Foundry, and Cantilux—to be approved, enabled, and eligible subject to per-evidence quarantine. Release validation is offline; source acquisition is not part of it.

## Identity and evidence diagnostics

The deterministic suite exercises identity reports, mappings, evidence families/facts, quarantine, conflicts, and activation state:

```bash
python -m pytest -q tests/test_identity_corpus_alpha61.py
python -m pytest -q tests/test_evidence_families_alpha62.py
python -m pytest -q tests/test_entity_retrieval_alpha63.py
python -m archie.cli sources conflicts
```

## Retrieval and source inspection

```bash
python -m archie.cli search "Giant Fly" --top-k 5
python -m archie.cli diagnose-retrieval "What is an Aboleth's Armor Class?" --top-k 5
python -m archie.cli sources show srd521
python -m archie.cli sources show open5e:srd-2024
python -m archie.cli sources show foundry:srd-5.2
python -m archie.cli sources show cantilux:dnd-srd-json
```

Activation is reversible through the existing `sources enable` and `sources disable` commands; tests verify that toggling a representation changes eligibility without deleting evidence or changing identity.

## Release gate

```bash
./scripts/release_check.sh
sha256sum -c SHA256SUMS
git diff --check
```

The release check is deterministic, offline, and does not require llama-server. Live generation is separate from release blocking; high-level ask/service tests use deterministic fixtures.

## Failure modes

- Pinned hash or provenance mismatch: hard stop.
- Missing/stale index: rebuild required.
- Ambiguous identity: quarantine.
- Conflicted evidence family: affected claim fails closed.
- No eligible retrieval evidence: do not verify the rule.
- Model unavailable or malformed output: no fallback to pretrained D&D knowledge.
