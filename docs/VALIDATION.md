# Validation strategy — v1.5

Archie uses three validation layers.

## Deterministic release tests

`python -m pytest` verifies source integrity, ingestion, character path containment, evidence-ID validation, Retrieval v2 behavior, known evidence coverage, multi-concept coverage, child-language aliases, neighbor expansion, llama.cpp request controls, and the answer-coverage fail-closed gate.

## Retrieval diagnostics

Known failure questions have expected evidence IDs. These tests verify that retrieval can place authoritative SRD passages in the evidence packet before involving Gemma.

## Live-model regression

Run:

```bash
./scripts/run_regression.sh
```

The 38-question suite writes `archie-regression-results.md` with status, elapsed time, answer, claims, and provenance. Review failures for correctness, grounding, restraint, source-boundary behavior, and false-premise correction.

Do not treat one successful demo as proof of reliability. Every observed failure should become a reproducible regression test before architecture or prompts are changed.
