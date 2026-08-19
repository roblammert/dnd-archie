# dnd-archie v1.5.1

Reliability patch for the SRD 5.2.1 evidence-gated local D&D player assistant.

## Release focus

v1.5.1 hardens structured-output handling and full-answer evidence coverage. It does not add new rules sources or broaden Archie's authority.

## Gates

- deterministic pytest suite must pass;
- SRD source hash must verify;
- index must remain bound to the approved source;
- malformed model contracts must fail closed rather than crash;
- every factual clause in a strict-audit answer must be explicitly certified;
- live Gemma regression should be rerun locally with `./scripts/run_regression.sh`.
