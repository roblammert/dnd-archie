# Archie v2.0.0-alpha.1 — Source Library Foundation

Alpha.1 generalizes Archie's storage layer from a single implicit SRD corpus to an explicit Source Library while keeping **SRD 5.2.1 as the only enabled rules authority**.

## Guarantees

- Existing SRD evidence IDs are preserved (`SRD521-P...`).
- Every evidence chunk is bound to a source, source version, authority type, and edition.
- The SRD PDF remains SHA-256 pinned before ingestion and retrieval.
- The index is generated data and is rebuilt from scratch on `archie ingest`.
- Gemma pretrained D&D knowledge remains non-authoritative.
- No Open5e integration exists in alpha.1.
- No multi-source conflict or precedence behavior exists in alpha.1.

## Schema

The SQLite index now includes `sources`, `source_versions`, `content_records`, `evidence_chunks`, and `evidence_fts`. A compatibility `metadata` table remains to preserve v1.6 source/index tamper detection.

## CLI

```bash
python -m archie.cli sources list
python -m archie.cli sources show srd521
python -m archie.cli sources verify
```

## SRD source manifest

`sources/srd521/source.yaml` is the canonical manifest for Source Library registration and integrity verification.
