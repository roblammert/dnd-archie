# Archie v2.0.0-alpha.6

- Package: `2.0.0a6`
- Base: `v2.0.0-alpha.5.1`
- Purpose: Single-authority multi-representation SRD identity, evidence, and retrieval release.
- Authority: `wotc:srd-5.2.1`

## Architecture

```text
WotC SRD 5.2.1
  -> canonical structured entities
  -> evidence families
  -> representation observations
  -> family-aware retrieval
```

Enabled representations are `wotc:official-srd-5.2.1`, `open5e:srd-2024`, `foundry:srd-5.2`, and `cantilux:dnd-srd-json`. PDF pages remain valid evidence containers without requiring canonical entity mapping.

## Expected evidence state

| Representation | Searchable | Quarantined |
|---|---:|---:|
| Official | 1,067 | 0 |
| Open5e | 2,820 | 76 |
| Foundry | 1,817 | 120 |
| Cantilux | 3,435 | 317 |
| **Total** | **9,139** | **513** |

The release retains 17 fail-closed provider discrepancies and quarantines 513 ambiguous evidence chunks. Representations never vote.

## Frozen fingerprints

- alpha.5.1 substantive corpus: `1ee9f26b61a32f74dade72116dff397109c49f859f2bd04386553128f9b7b27f`
- alpha.6.1 identity: `0f096b45de75264a31b1746981c9ea92f21a6a51973dd2534c63778ccc18825a`
- alpha.6.2 evidence: `7664ae39a44558b04c5ca0fbe6978725925c89a32532077829866dcc7388b696`
- alpha.6.3 activation: `1db7c0b622133a5d92f8c465f3221622cc157122bcf26904966a87521e99b267`
