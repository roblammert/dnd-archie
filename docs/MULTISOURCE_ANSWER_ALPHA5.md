# Alpha.5 — Multi-Source Answer Integration

Alpha.5 turns alpha.4's approved multi-source retrieval pool into a source-aware answer service without changing source approval, licensing, edition isolation, or the v1.6 fail-closed audit contract.

## Answer authority modes

Every successful answer derives its source mode from evidence IDs actually cited by the answer claims:

- `official_only` — all cited evidence is `official_srd`;
- `supplemental_only` — cited evidence is approved supplemental content and no official SRD evidence is cited;
- `mixed` — both official and supplemental evidence are cited;
- `none` — no rules evidence was cited.

Retrieved but unused evidence is never reported as a source used by the answer.

## Authority behavior

The official SRD remains higher priority than approved supplements. Supplemental-only answers are valid when approved supplemental evidence is the only retrieved evidence that establishes the requested fact. Mixed answers are allowed only when each factual claim is independently supported by its cited evidence.

Gemma is never allowed to reconcile or invent around source disagreements.

## Conflict policy

If primary evidence contains same-named structured records of the same content type from multiple approved/enabled sources and their stored canonical JSON differs, Archie fails closed before calling the LLM. Alpha.5 does not attempt semantic conflict resolution.

## Duplicate suppression

Whitespace-equivalent evidence text is suppressed before answer generation. Retrieval ranking determines the survivor, so higher-priority official evidence wins when duplicate evidence is otherwise equivalent.

## Player-facing provenance

The CLI now displays the exact sources cited by answer claims plus the authority mode. This is deterministic application metadata, not model-generated provenance.

## Non-goals

Alpha.5 does not add the web UI, additional Open5e documents, 2014 fallback, semantic source-merging, or model-memory authority.
