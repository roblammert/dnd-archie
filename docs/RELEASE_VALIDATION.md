# v1.6.0-rc.1 release validation

Dev.4 is the release-candidate hardening build from dev.3.

Required deterministic gates:

```bash
./scripts/release_check.sh
```

This verifies the pinned SRD source, rebuilds the index, runs the complete deterministic test suite, compiles the code, and runs retrieval smoke checks.

Required live Gemma acceptance:

```bash
./scripts/run_regression.sh
./scripts/run_epistemic_regression.sh
```

Acceptance targets:

- Existing 38-question baseline remains semantically acceptable.
- Existing 7-question epistemic suite remains acceptable.
- `Can I use a longbow while Prone?` must not infer permission from Disadvantage or absence of prohibition.
- A single malformed auditor JSON response should be retried once; a repeated malformed response must fail closed.
