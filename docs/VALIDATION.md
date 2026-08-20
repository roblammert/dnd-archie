# Validation strategy — v2.0.0-alpha.6

Alpha.6 release validation is deterministic, offline, and run from the repository `.venv`.

## Required gates

- Pinned source hashes, importer provenance, one-authority admission, and all four enabled representations.
- Identity taxonomy and canonical mappings, including false-merge boundaries, cross-type disambiguation, and ambiguity quarantine.
- Deterministic evidence families and allowlisted field facts, including field aliases and claim-scoped conflicts.
- Duplicate suppression and explicit no-voting behavior; a family's best member score is used rather than a provider-score sum.
- Family-aware retrieval, entity budgets, evidence-kind selection, and reversible representation activation.
- End-to-end deterministic CLI/core ask acceptance, including pass, fail-closed, ambiguous, and representation-specific cases.
- Pi contract requiring fresh Archie retrieval for every new D&D rules-fact question.
- Two clean rebuilds with matching substantive, identity, evidence, and activation fingerprints.
- Expected searchable, FTS, quarantine, conflict, authority, and representation counts.
- Package-version consistency, complete pytest, release check, `SHA256SUMS`, and `git diff --check`.

The high-level acceptance matrix covers Fireball range; Aboleth HP, AC, and CR; Giant Fly; Elf; Resistance; Awaken school; Sorcerer progression; fail-closed Awaken casting time and Dart weight; unavailable ambiguous Acid; and PDF-only, Open5e-only, Foundry-only, Cantilux-only, and mixed-representation provenance. Every usable answer renders one SRD authority.

## Frozen fingerprints

- substantive: `1ee9f26b61a32f74dade72116dff397109c49f859f2bd04386553128f9b7b27f`
- identity: `0f096b45de75264a31b1746981c9ea92f21a6a51973dd2534c63778ccc18825a`
- evidence: `7664ae39a44558b04c5ca0fbe6978725925c89a32532077829866dcc7388b696`
- activation: `1db7c0b622133a5d92f8c465f3221622cc157122bcf26904966a87521e99b267`

Final run results belong in `docs/RELEASE_VALIDATION.md`; do not copy an earlier test total into that record.
