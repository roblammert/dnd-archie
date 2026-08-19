# Archie v1.5.1 Reliability Patch

v1.5.1 is a reliability-only patch over v1.5.0. It does not broaden Archie's rules authority beyond SRD 5.2.1.

## Problems addressed

The v1.5 live regression exposed four remaining reliability classes:

1. malformed model claims could terminate the CLI (`missing evidence_ids`);
2. harmless model formatting drift could terminate the CLI (`invalid kind`);
3. the answer could infer permission from a rule that only established a penalty;
4. related but distinct mechanics such as targeting, attack rolls, visibility, and sight-required effects could be conflated.

## Behavior changes

- Answer structures are normalized only for harmless casing/whitespace drift.
- Invalid structures receive one bounded correction retry using the same evidence packet.
- If that retry fails, Archie returns `PARTIAL` and refuses to guess rather than exiting with a contract error.
- The auditor must enumerate independently factual answer clauses as `answer_units` and certify each one.
- Missing or unsupported answer units fail closed.
- Permission/prohibition must be established by evidence; a penalty alone is insufficient.
- Targeting, attacks, visibility, and sight-required effects remain distinct unless the SRD evidence explicitly connects them.

## Acceptance tests

Run:

```bash
pytest -q
./scripts/run_regression.sh
```

The four v1.5 failures are recorded in `tests/live_regression_v151.json` for repeated local Gemma validation.
