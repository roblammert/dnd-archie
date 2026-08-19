# Open5e Discovery — v2.0.0-alpha.2

## Scope

Alpha.2 adds **discovery and inventory only**. It does not import Open5e game content into Archie's Source Library, does not create evidence chunks from Open5e, and does not make Open5e an enabled rules authority.

## Why Open5e V2

Open5e V2 is the maintained API. Archie uses the explicit `/v2` prefix and the `/v2/documents` catalog. Open5e resources carry a nested `document` object with a unique `key`, and resource endpoints can be filtered by `document__key__in=<key>`.

## Commands

```bash
archie sources discover open5e
archie sources discover open5e --json
archie sources inventory open5e
archie sources inventory open5e --document srd-2024
archie sources inventory open5e --document srd-2024 --json
```

`discover` performs a live metadata/count inventory and writes an immutable timestamped snapshot plus `data/discovery/open5e/latest.json`.

`inventory` reads the local snapshot only. It does not contact Open5e.

## Inventory categories

Alpha.2 counts the following V2 API resources per source document without downloading full records:

- base classes
- subclasses
- species
- spells
- backgrounds
- feats
- equipment/items
- magic items
- rules
- conditions
- creatures

Counts are obtained with the document filter and `limit=1`; only Open5e's result count is retained.

## Provenance captured

For each Open5e document Archie records, when supplied by the API:

- document key and name
- document type
- publisher metadata
- license metadata
- game-system metadata
- author
- publication date
- permalink
- per-resource counts
- discovery timestamp
- API version/base URL
- snapshot SHA-256

## Licensing boundary

Open5e's software license is not assumed to be the license for every game-content document. Alpha.2 records each document's own license metadata for review. **Discovery does not mean approval.** Alpha.3 must require an explicit eligibility/approval decision before any document can be imported.

## Trust boundary

The only enabled/searchable rules authority remains `srd521`. Open5e discovery snapshots are not queried by `archie search` or `archie ask`, and Gemma never sees the discovery catalog as rules evidence.
