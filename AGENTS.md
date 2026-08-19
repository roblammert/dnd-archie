# Archie Agent Contract — v2.0.0-alpha.4

## Purpose

Archie is a player-facing D&D assistant whose rules authority comes only from explicitly approved and enabled local evidence sources.

## Frozen trust rules

- Gemma pretrained D&D knowledge is never a rules authority.
- Every rules claim must be grounded in enabled local evidence and pass the existing audit contract.
- Fail closed rather than guess.
- Preserve source identity and provenance through retrieval and audit.

## v2 Source Library state

- `srd521` is the only approved and enabled rules authority in alpha.3.
- `open5e:srd-2024` may be imported only as disabled structured content.
- Import is not approval. Approval is not enablement.
- Open5e imports must create zero evidence chunks in alpha.3.
- Never feed imported Open5e content to the LLM as rules evidence.
- Missing license metadata must remain visible and must block automatic approval/enabling.
- Raw Open5e JSON and provider/document identity must be preserved for provenance and reprocessing.
- Other Open5e document keys are outside alpha.3 import policy.

## Alpha.3 scope boundary

Allowed: discovery, explicit `srd-2024` import, raw snapshots, structured records, hashes/versions, disabled manifests, inspection, deterministic tests.

Not allowed: Open5e authority activation, evidence generation, source mixing, web UI, house-rule precedence, edition fallback.
