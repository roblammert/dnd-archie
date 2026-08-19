# Archie v2.0.0-alpha.1 — Agent Contract

This repository is the first Archie v2.0 development alpha. It preserves the frozen v1.6 trust engine while introducing a generic local Source Library.

## Non-negotiable trust rules

- Gemma pretrained D&D knowledge is never a rules authority.
- Rules claims must be grounded in enabled, approved local evidence and pass the existing audit path.
- Fail closed rather than guess.
- Preserve source identity, authority type, edition, version, and evidence IDs end-to-end.
- Do not silently mix editions or source authorities.

## Alpha.1 scope

- `srd521` is the only enabled source.
- `srd521` authority type is `official_srd`; edition is `2024`.
- Open5e is intentionally absent.
- No web application code belongs in alpha.1.
- No house-rule precedence, 2014 fallback, or source-conflict resolution belongs in alpha.1.
- The SQLite index is generated data and may be rebuilt from source manifests/content.

## Architecture direction

CLI and future web interfaces must call the same Archie core services. Do not put rules, retrieval, or authority logic into presentation layers.
