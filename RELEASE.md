# Archie v2.0.0-alpha.5

**Milestone:** Multi-Source Answer Integration

Alpha.5 keeps the alpha.4 Source Library lifecycle unchanged and adds source-aware behavior to the answer service. Answers now report only the authorities actually cited by their claims, support approved supplemental-only answers, distinguish mixed-source answers, suppress exact duplicate evidence, and fail closed on conflicting same-entity structured records.

Release gate target: all inherited trust/source tests plus alpha.5 supplemental-only, mixed-source, duplicate-suppression, deterministic provenance, and conflict fail-closed tests.

The web application is intentionally not included.
