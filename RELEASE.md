# dnd-archie v1.6.0-rc.1

Final reliability release candidate from v1.6.0-dev.4.

## Scope

No retrieval, evidence-authority, epistemic, permission, or player-feature changes are introduced. rc.1 changes only malformed auditor structured-output recovery and observability.

## Auditor repair

The initial evidence audit uses the normal auditor. If and only if that response is malformed structured output, Archie performs one repair-specific re-audit using the same question, evidence, player-facing answer, premises, and claims. The compact repair contract explicitly lists the required premise and claim indexes and requires JSON only.

If the correction succeeds, provenance includes `Audit structured-output correction succeeded.` If the correction is also malformed, Archie fails closed as `PARTIAL` and provenance explicitly records that both attempts were malformed. Transport/server failures remain operational errors.

## Acceptance

Run:

```bash
./scripts/release_check.sh
./scripts/run_regression.sh
./scripts/run_epistemic_regression.sh
```

The 38-question baseline and 7-question epistemic live suites are unchanged.
