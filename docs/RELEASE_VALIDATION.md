# v2.0.0-alpha.6 release validation

- Package: `2.0.0a6`
- Base: `v2.0.0-alpha.5.1`
- Authority: `wotc:srd-5.2.1`
- Representations: 4 enabled
- Expected searchable evidence/FTS: 9,139
- Expected quarantined evidence: 513
- Expected retained fail-closed conflicts: 17

Release validation uses the repository `.venv`, committed pinned artifacts, and no network or live model:

```bash
source .venv/bin/activate
./scripts/release_check.sh
sha256sum -c SHA256SUMS
git diff --check
```

Required gates include identity false-merge checks, ambiguity quarantine, evidence-family determinism, duplicate/no-voting behavior, field-scoped conflict handling, activation reversibility, field aliases, cross-type disambiguation, deterministic CLI/core ask acceptance, Pi fresh-retrieval wording, and two rebuilds matching all four frozen fingerprints.

## Final release-preparation results (2026-08-20)

- Package declarations and tracked package metadata: `2.0.0a6`, consistent.
- Complete pytest: 303 passed in 186.19 seconds; release-check rerun: 303 passed in 183.91 seconds.
- Source verification: four enabled pinned sources verified.
- Release check: `Archie v2.0.0-alpha.6 deterministic release checks PASS`.
- Targeted ask/activation suite: 72 passed, covering the acceptance matrix and reversible activation.
- Two clean rebuilds: all four fingerprints matched each other and their frozen values.
- Authority set: only `wotc:srd-5.2.1`; representations: the exact four expected IDs, all approved, licensed, and enabled.
- Searchable/FTS evidence: 9,139 (Official 1,067; Open5e 2,820; Foundry 1,817; Cantilux 3,435).
- Quarantined evidence: 513 (Open5e 76; Foundry 120; Cantilux 317); quarantined evidence has no eligible FTS documents.
- Retained conflicted families: 17, fail closed.
- Representative retrieval medians: Attack 115.00 ms; Giant Fly 82.89 ms; Elf 68.54 ms; Aboleth HP 97.66 ms; class progression 85.66 ms. No obvious retrieval regression or N+1 behavior was observed.
- Scope audit against `v2.0.0-alpha.5.1`: limited to the planned identity/taxonomy, evidence/facts/quarantine/conflict, family-aware retrieval/activation, authority-first provenance, Pi/CLI grounding/acceptance, and release preparation work; prohibited feature categories were absent.
- `SHA256SUMS` verification, deterministic regeneration comparison, and `git diff --check`: PASS.
