# Cantilux dnd-srd-json source

Archie pins `https://github.com/Cantilux/dnd-srd-json` at commit
`df536fe94c92cff49cc531f7283f6995b881fefa`. The committed raw file is the
upstream repository's canonical complete bundle, `data/srd.json`, copied
byte-for-byte. Its SHA-256 is
`50a65517978e0ea47758c319f1848f7b40b609784fb2cf7b09079d66a0ecb219`.

The upstream bundle independently repeats its corpus identity in `manifest`
and `metadata`: package `dnd-srd-json`, SRD version `5.2.1`, rules revision
`2024`, official SRD URL `https://www.dndbeyond.com/srd`, and license
`CC-BY-4.0`. The upstream `LICENSE` and `NOTICE.md` attribute the material to
Wizards of the Coast LLC. Cantilux contains no per-record license field, so
Archie validates this corpus-level provenance before any records are admitted.
A conflict or missing field fails the whole import closed.

The repository publishes documents, sections, collections, granular resources,
and generated resource/search indexes. Archie normalizes the items in its 20
resource collections because they are meaningful future retrieval units and
carry stable IDs plus document/section paths. It does not separately normalize
duplicate document and section projections or generated indexes. A record's
`upstream_id` is its collection-local Cantilux `id`; its retained
`upstream_path` is the documented granular path
`data/resources/<collection>/<id>.json`.

At the pinned revision, six resources (`cone`, `cube`, `cylinder`, `emanation`,
`line`, and `sphere`) are canonically contained and indexed under
`areas-of-effect` but their raw internal `collection` field says
`area-of-effects`. This is an isolated upstream compatibility quirk, not an
official alias. Archie admits only these six pinned identities when the
manifest, item IDs, lightweight items, audited resource/search index identity,
and document/section lineage all corroborate the canonical container. The
normalized collection remains `areas-of-effect`; the unmodified structured
record retains the bad raw field. Every other collection mismatch fails closed.

To reproduce the snapshot from an already checked-out pinned repository:

```console
.venv/bin/python -m archie.cli sources acquire cantilux \
  --checkout /path/to/dnd-srd-json \
  --output sources/cantilux/dnd-srd-json/raw/cantilux-dnd-srd-json-df536fe94c92.json
```

Omit `--checkout` to fetch the immutable commit. Acquisition verifies `HEAD`,
validates corpus identity, and preserves the canonical upstream bytes.
In alpha.6, the pinned Cantilux representation is enabled and contributes evidence subject to deterministic identity mapping and ambiguity quarantine.
