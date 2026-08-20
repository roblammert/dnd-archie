# v2.0.0-alpha.5.1 release validation

- Package: `2.0.0a5.post1`
- Base: `v2.0.0-alpha.5`
- Authority: `wotc:srd-5.2.1`
- Representations: 4
- Expected normalized corpus: 6,902 records
- Expected evidence: 3,963 chunks
- Searchable: official + Open5e
- Non-searchable: Foundry + Cantilux

Required deterministic gates:

```bash
./scripts/release_check.sh
```

This verifies the pinned SRD source, rebuilds the index, runs the complete deterministic test suite, compiles the code, and runs retrieval smoke checks.

The deterministic gate verifies pinned artifacts, rebuilds the index, runs the complete suite, compiles code, and runs retrieval/source smoke checks. It requires the repository `.venv` on `PATH` and no network or live model.

Optional live Gemma acceptance inherited from alpha.5:

```bash
./scripts/run_regression.sh
./scripts/run_epistemic_regression.sh
```

Final deterministic results (2026-08-20):

- Complete pytest suite: 198 passed.
- Enabled-source verification: 2 enabled sources verified.
- Release check: PASS.
- Two clean rebuilds: matching substantive fingerprint `1ee9f26b61a32f74dade72116dff397109c49f859f2bd04386553128f9b7b27f`.
- WotC-only authority, exact four-representation set, 6,902 records, and 3,963 evidence chunks: PASS.
- Foundry/Cantilux evidence and FTS quarantine: PASS.
- Open5e repeat rehydration: PASS.
