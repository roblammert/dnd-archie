# v1.0.0 release validation

Release date: 2026-08-19

Validated in the build environment:

- Approved SRD SHA-256: PASS
- PDF pages extracted: 364
- Evidence chunks generated: 1,067
- SQLite FTS5 retrieval: PASS
- Passive Perception retrieval sanity check: PASS
- Source/index hash binding: PASS
- Invented evidence-ID rejection: PASS
- Character path containment: PASS
- Python compile check: PASS
- Deterministic pytest suite: 9 passed

Not validated in the build environment:

- Connection to the user's actual llama-server
- Gemma4-12B live answer quality
- Pi startup against the user's installed 0.84.2 runtime

Run `python scripts/live_regression.py` after connecting the local model, then add observed failures to the regression suite before treating the assistant as player-ready.
