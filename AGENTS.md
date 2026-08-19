# Archie Agent Contract — v2.0.0-alpha.2

## Purpose

Archie is a player-facing D&D assistant whose rules authority comes only from explicitly enabled local evidence sources.

## Frozen trust rules

- Gemma pretrained D&D knowledge is never a rules authority.
- Every rules claim must be grounded in enabled local evidence and pass the existing audit contract.
- Fail closed rather than guess.
- Preserve source identity and provenance through retrieval and audit.

## v2 Source Library state

- `srd521` is the only enabled rules authority in alpha.2.
- Open5e integration in alpha.2 is **discovery/inventory only**.
- Open5e discovery snapshots are not evidence sources.
- Never feed Open5e discovery metadata or counts to the LLM as rules evidence.
- Never create an Open5e `source.yaml`, `content_record`, or `evidence_chunk` from discovery alone.
- A document appearing in Open5e does not mean Archie approves it for import.
- Preserve each discovered document's license metadata separately from the Open5e software license.

## Alpha.2 scope boundary

Allowed: Open5e V2 document discovery, provenance metadata, resource counts, local discovery snapshots, CLI inspection, tests.

Not allowed: Open5e content import, source approval/enabling, source mixing, web UI, house-rule precedence, edition fallback.
