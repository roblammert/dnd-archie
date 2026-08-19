---
name: archie-source-integrity
description: Verifies that Archie's local D&D SRD PDF exactly matches the pinned approved SHA-256 and checks ingestion prerequisites. Use before source migration, debugging, release validation, or when source integrity is questioned.
---


# Archie Source Integrity

Run:
```bash
python -m archie.cli verify-source
python -m archie.cli doctor
```

A SHA-256 mismatch is a hard trust failure. Do not ingest or answer rules until the approved manifest is deliberately updated as part of a source-version migration.
