# dnd-archie-v1.5.1

**Archie** is a local, evidence-gated D&D player assistant for Pi and an OpenAI-compatible local LLM server. Its sole authority for D&D rules is the bundled **Dungeons & Dragons SRD 5.2.1** PDF.

Archie does not pretend the model has forgotten D&D. Instead, it separates **authority** from **intelligence**: Gemma may explain, teach, interpret informal language, and reason, but every factual D&D rule must be supported by retrieved SRD evidence.

## v1.5 reliability architecture

- SRD 5.2.1 is SHA-256 pinned and is the only rules authority.
- SQLite FTS5 provides deterministic local retrieval.
- Retrieval v2 performs stop-word cleanup, exact concept matching, definition/section boosting, multi-concept coverage, and cross-page neighbor expansion.
- A small child-language alias layer maps phrases such as `armor number` to `Armor Class` for search only.
- Every rules claim must cite retrieved evidence IDs.
- Evidence IDs are validated in Python; invented citations fail closed.
- The strict audit checks both the structured claims **and the player-facing answer**, preventing unsupported mechanics from escaping merely by being omitted from `claims[]`.
- llama.cpp JSON output is constrained with `response_format`, generation is capped, and model thinking is disabled for fast deterministic rules work.
- If evidence is insufficient, Archie returns `PARTIAL` or `NOT_IN_SRD` rather than guessing.

## Requirements

- Linux/macOS/WSL with Python 3.11+
- Pi, if you want the Pi interface
- An OpenAI-compatible local chat endpoint such as llama-server
- A local model such as `gemma4-12b-it-q4_k_m`

## First run

```bash
cd dnd-archie-v1.5.1
./scripts/bootstrap.sh
source .venv/bin/activate
python -m archie.cli doctor
python -m archie.cli ask "What happens when I have advantage on a roll?"
```

Copy `.env.example` to `.env` and adjust your endpoint if necessary:

```bash
cp .env.example .env
```

Typical configuration:

```dotenv
ARCHIE_LLM_BASE_URL=http://127.0.0.1:61000/v1
ARCHIE_LLM_MODEL=gemma4-12b-it-q4_k_m
ARCHIE_LLM_TIMEOUT=300
ARCHIE_LLM_MAX_TOKENS=768
ARCHIE_TOP_K=6
ARCHIE_RETRIEVAL_CANDIDATE_K=36
ARCHIE_NEIGHBOR_RADIUS=1
ARCHIE_STRICT_AUDIT=1
```

Shell environment variables override `.env` values.

## Useful commands

```bash
python -m archie.cli verify-source
python -m archie.cli ingest
python -m archie.cli search "prone condition"
python -m archie.cli diagnose-retrieval "What does Prone do?"
python -m archie.cli ask "What does Prone do?"
python -m archie.cli characters
```

`diagnose-retrieval` exposes the deterministic query plan, aliases/concepts detected, primary evidence, adjacent context, and scores. It is intended for debugging retrieval without weakening the evidence gate.

## Pi usage

Start Pi from the repository root so it loads `AGENTS.md`, `.pi/APPEND_SYSTEM.md`, and `.pi/skills/`:

```bash
cd dnd-archie-v1.5.1
pi
```

For the strongest source-lock guarantee, route rules questions through the local CLI or `archie-rules` skill.

## Validation

Deterministic release checks:

```bash
./scripts/release_check.sh
```

Live-model regression report:

```bash
./scripts/run_regression.sh
```

The live regression writes `archie-regression-results.md` for review.

## Repository map

```text
AGENTS.md                 Durable project rules for Pi
.pi/APPEND_SYSTEM.md      Pi runtime authority contract
.pi/skills/               Pi Agent Skills
archie/concepts.py        Canonical retrieval concepts + language aliases
archie/retrieve.py        Retrieval v2 and diagnostics
archie/answer.py          Evidence binding + strict answer/claim audit
sources/                   Approved SRD PDF + immutable manifest
data/index/                Rebuildable local SQLite index
data/characters/           Human-readable character YAML
scripts/                    Setup, validation, and regression helpers
tests/                      Deterministic reliability tests
docs/                       Architecture, retrieval, operations, validation
```

## Important distinction

Archie may say: **“That option is not covered by the SRD evidence I have, so I can't verify its rules.”** It must not say: **“That option does not exist in D&D.”**

## License and source attribution

Project code is MIT licensed. The included SRD is a separate work distributed under CC-BY-4.0. See `sources/ATTRIBUTION.md` and the attribution material inside the PDF.
