# v2.0.0-alpha.2 Release Validation

## Deterministic release result

- SRD 5.2.1 integrity: PASS
- Enabled local authorities: 1 (`srd521`)
- SRD pages: 364
- SRD content records: 364
- SRD evidence chunks: 1,067
- Deterministic tests: 66/66 PASS
- Python compilation: PASS
- Retrieval smoke tests: PASS
- Open5e discovery tests: PASS via `httpx.MockTransport`

## Alpha.2 trust assertions

- Open5e uses explicit API V2 configuration.
- Discovery captures document provenance and resource counts only.
- Discovery snapshots are not registered local sources.
- No Open5e content records or evidence chunks are created.
- `archie search` and `archie ask` continue to operate only on the enabled local Source Library.
- SRD 5.2.1 remains the sole enabled rules authority.
- No web application code is included.

## Live acceptance

The package includes `scripts/run_open5e_discovery.sh`. Run it on a network-connected installation to exercise the real Open5e V2 API and create `open5e-discovery-results.md`. The report records the discovered documents, per-resource counts, source/license metadata, and verifies that the local authority list is unchanged before and after discovery.
