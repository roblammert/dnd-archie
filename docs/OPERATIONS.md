# Operations — v1.5

## llama-server

Archie expects an OpenAI-compatible `/v1/chat/completions` endpoint. Configuration is loaded from the repo-root `.env`; existing shell environment variables take precedence.

```bash
cp .env.example .env
```

The llama.cpp request contract uses JSON-object response formatting, a bounded completion token count, and `enable_thinking=false` to keep local inference fast and predictable.

Archie does not start or manage llama-server itself.

## Rebuild the index

```bash
python -m archie.cli verify-source
python -m archie.cli ingest
```

The index is a disposable derived artifact. The source PDF is never modified.

## Diagnose retrieval

```bash
python -m archie.cli diagnose-retrieval "What does Prone do?"
```

Use diagnostics before changing prompts. A `NOT_IN_SRD` result for material known to be present usually indicates retrieval coverage, not a need to weaken the evidence policy.

## Source migration

Do not replace the PDF in place. A future SRD version should be a deliberate migration with a new source filename, SHA-256, authority ID, tests, and version bump.

## Failure modes

- SHA mismatch: hard stop.
- Missing or stale index: hard stop with instruction to ingest.
- No retrieval hits: refusal to verify.
- LLM unavailable: hard error; no fallback to pretrained D&D knowledge.
- Malformed JSON: hard error; no unverified prose fallback.
- Invented evidence ID: hard error.
- Unsupported structured claim: fail-closed `PARTIAL`.
- Unsupported factual mechanic in player-facing answer: fail-closed `PARTIAL`.
