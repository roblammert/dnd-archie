# Alpha.4 Multi-Source Trust Engine

## Goal

Allow explicitly approved local supplemental sources to participate in Archie answers without weakening the v1.6 evidence firewall.

## State machine

`imported` does not imply `approved`; `approved` does not imply `enabled`. An external source becomes searchable only when its manifest and SQLite state both show approved, enabled, license metadata present, and an edition compatible with the active edition.

## Open5e evidence

Open5e structured `content_records` are converted into stable local evidence chunks only during explicit enablement. Evidence IDs include provider document, content type, provider record identifier, a stable digest, and chunk sequence. Raw provider JSON remains the persistent reprocessing source.

## Authority precedence

`official_srd` has higher retrieval priority than `approved_supplement`. Supplemental evidence remains eligible when the canonical PDF does not contain the relevant structured hit. Evidence packets expose source ID, authority type, and edition to both answer generation and audit. The model is instructed never to merge conflicting rules into a hybrid.

## Edition isolation

`ARCHIE_ACTIVE_EDITION` defaults to `2024`. Retrieval filters out evidence from other editions even if a source is otherwise enabled.

## Rebuild behavior

SQLite remains generated storage. Re-ingestion rebuilds the SRD index and rehydrates stored Open5e snapshots. If an external manifest is approved+enabled+licensed, its structured records and evidence chunks are reconstructed. Invalid enabled authorization state fails closed.

## Hash meanings

The raw snapshot byte hash and canonical provider-content hash are intentionally separate and are labeled separately by `sources show`.
