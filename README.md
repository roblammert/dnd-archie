# dnd-archie-v1.0.0

**Archie** is a local, evidence-gated D&D player assistant built for Pi and an OpenAI-compatible local LLM server (tested by design against a Gemma-family chat model). Its sole authority for D&D rules is the bundled **Dungeons & Dragons SRD 5.2.1** PDF.

Archie is intentionally *not* an AI that pretends to forget everything it learned during pretraining. The model may use general intelligence for language, teaching, analogies, question interpretation, and reasoning. It may establish a D&D rule fact only from evidence retrieved from the approved SRD corpus.

## Trust contract

- **SRD 5.2.1 is the only rules authority.**
- Pretrained D&D knowledge is never authoritative.
- Every rules answer must retrieve evidence first.
- Every factual rules claim must cite one or more retrieved evidence IDs.
- Evidence IDs are validated by code; invented citations cause the answer to fail closed.
- A second evidence-only audit is enabled by default.
- If evidence is insufficient, Archie says so instead of guessing.
- Character YAML may supply player-specific facts, but cannot override rules.
- Arithmetic and derivations are labeled `DERIVED`.
- Content not present in SRD 5.2.1 is reported as `NOT_IN_SRD`, not as nonexistent in D&D.

This architecture can make hallucination **very low and visible**, but no generative LLM should be advertised as mathematically incapable of hallucination.

## Requirements

- Linux/macOS/WSL with Python 3.11+
- Pi, if you want the Pi interface
- A local OpenAI-compatible chat endpoint, typically llama-server
- Your local Gemma model (for example `gemma4-12b-it-q4_k_m`)

Python dependencies are deliberately small: `PyMuPDF`, `PyYAML`, and `httpx`.

## First run

```bash
cd dnd-archie-v1.0.0
./scripts/bootstrap.sh
source .venv/bin/activate
python -m archie.cli doctor
python -m archie.cli ingest
python -m archie.cli search "passive perception"
python -m archie.cli ask "Explain advantage like I'm 10."
```

Default LLM endpoint: `http://127.0.0.1:8080/v1/chat/completions`.

Override it with environment variables:

```bash
export ARCHIE_LLM_BASE_URL=http://127.0.0.1:8080/v1
export ARCHIE_LLM_MODEL=gemma4-12b-it-q4_k_m
```

## Pi usage

Start Pi **from the repository root** so it loads `AGENTS.md`, `.pi/APPEND_SYSTEM.md`, and `.pi/skills/`.

```bash
cd dnd-archie-v1.0.0
pi
```

Normal questions can be conversational. Pi can discover the project skills automatically, or you can force a skill with commands such as:

```text
/skill:archie-rules What does prone do?
/skill:archie-explain Explain concentration to a 10-year-old.
/skill:archie-character-calc Calculate passive perception for data/characters/example-ranger.yaml.
```

For the strongest source-lock guarantee, use `python -m archie.cli ask ...` or the `archie-rules` skill, both of which route through the evidence-gated answer engine. Free-form Pi behavior is additionally constrained by `AGENTS.md` and `SYSTEM.md`, but a harness prompt alone is never as strong as code enforcement.

## Repository map

```text
AGENTS.md                 Durable project rules for Pi
.pi/APPEND_SYSTEM.md      Strict Archie runtime persona/authority contract
.pi/skills/               Pi Agent Skills
archie/                    Retrieval, ingestion, answer, audit, character code
sources/                   Approved source PDF + immutable manifest
prompts/                   Answer/audit prompt contracts
data/index/                Generated SQLite index (gitignored)
data/characters/           Human-readable player YAML files
scripts/                   Setup, ingestion, validation helpers
tests/                     Deterministic and optional live-model tests
docs/                      Architecture, trust model, operations
```

## Important distinction

Archie may say: “That option is not covered by SRD 5.2.1, so I can't verify its rules.” It must **not** say: “That option does not exist in D&D.”

## License and source attribution

The project code is MIT licensed. The included SRD is a separate work distributed under CC-BY-4.0. See `sources/ATTRIBUTION.md` and the copyright/attribution material inside the source PDF.
