# Operations

## llama-server

Archie expects an OpenAI-compatible `/v1/chat/completions` endpoint. Point `ARCHIE_LLM_BASE_URL` at the server base URL and set `ARCHIE_LLM_MODEL` to the model identifier your server accepts.

Archie does not start or manage llama-server itself. This intentionally avoids coupling the project to one model path, GPU configuration, context size, or llama.cpp release.

## Rebuild the index

```bash
python -m archie.cli verify-source
python -m archie.cli ingest
```

Ingestion destroys and recreates the local chunk corpus. The source PDF is never modified.

## Source migration

Do not replace the PDF in-place. A future SRD version should be a deliberate project migration with a new source filename, SHA-256, authority ID, tests, and version bump.

## Failure modes

- SHA mismatch: hard stop.
- Missing index: hard stop with instruction to ingest.
- No retrieval hits: `NOT_IN_SRD`-style refusal to verify.
- LLM unavailable: hard error; no fallback to model memory.
- malformed model JSON: hard error; no unverified prose fallback.
- invented evidence ID: hard error.
- audit rejects a claim: fail-closed `PARTIAL` response.
