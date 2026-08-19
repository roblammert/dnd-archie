# Open5e Selective Import — Alpha.3

## Trust boundary

Alpha.3 introduces local possession of selected Open5e structured content without granting that content rules authority.

The only allowed Open5e document key is `srd-2024`. Import creates a persistent raw JSON snapshot plus normalized SQLite `content_records`, but it creates no `evidence_chunks`.

State is explicit:

- **imported**: a local raw snapshot and structured records exist;
- **approved**: a future policy decision has accepted the source as eligible authority;
- **enabled**: a future policy decision allows the source to participate in retrieval.

Alpha.3 always sets imported Open5e sources to `approved=false` and `enabled=false`.

## License gate

Open5e discovery may omit per-document license metadata. Alpha.3 records this as `license_status=missing`. Missing license metadata blocks automatic approval and enablement. Import itself is still allowed for the explicitly permitted `srd-2024` candidate so provenance and structure can be inspected locally before alpha.4.

## Persistent storage

Raw provider responses are stored under:

`/sources/open5e/<document-key>/raw/`

Each import receives a SHA-256 identity derived from the canonical document + resource payload. Re-importing unchanged content does not create a duplicate active source version or duplicate normalized records.

SQLite remains generated storage. A full SRD re-ingestion can rehydrate imported Open5e records from the persistent raw snapshot and manifest.

## Retrieval boundary

Retrieval continues to require `sources.enabled=1`. Alpha.3 creates zero Open5e evidence chunks, so imported records cannot enter FTS, evidence packets, Gemma generation, or the evidence auditor.
