# v1.5.1 release validation

Release date: 2026-08-19

Validated in the build environment:

- Approved SRD SHA-256: PASS
- PDF pages extracted: 364
- Evidence chunks generated: 1,067
- SQLite FTS5 index: PASS
- Retrieval v2 known-evidence coverage: PASS
- Multi-concept retrieval: PASS
- Cross-page neighbor expansion: PASS
- Child-language alias mapping: PASS
- Source/index hash binding: PASS
- Invented evidence-ID rejection: PASS
- Answer-coverage fail-closed gate: PASS
- llama.cpp JSON/thinking/output-cap request contract: PASS (mocked deterministic test)
- Character path containment: PASS
- Python compile check: PASS
- Deterministic pytest suite: **21 passed**
- Editable package discovery/install metadata: PASS in build environment

Not validated in the build environment:

- Connection to the user's actual llama-server on port 61000
- Full live Gemma4-12B v1.5 regression output
- Pi startup against the user's installed runtime

Run `./scripts/run_regression.sh` against the user's local model before declaring v1.5 player-ready.
