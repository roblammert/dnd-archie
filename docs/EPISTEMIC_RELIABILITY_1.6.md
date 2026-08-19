# Archie v1.6 Epistemic Reliability

v1.6 begins from the locked v1.5.1 baseline. It does not broaden Archie's rules authority: SRD 5.2.1 remains the sole D&D rules source.

## Problem addressed

A grounded assistant must distinguish three different situations when a player embeds a proposition in a question:

1. **SUPPORTED** — supplied SRD evidence establishes the proposition.
2. **CONTRADICTED** — supplied SRD evidence establishes that the proposition is false.
3. **UNRESOLVED** — supplied SRD evidence establishes neither the proposition nor its negation.

The critical rule is non-entailment: failure to establish X is not evidence for not-X, and failure to establish not-X is not evidence for X.

## Example

Question: `If I am Invisible, nobody can ever target me, right?`

The Invisible rules establish effects involving visibility and attack rolls, but those facts alone do not settle a universal proposition about all targeting. Archie should therefore classify the broad premise as UNRESOLVED unless retrieved SRD evidence directly settles it, then state only the narrower mechanics the evidence positively supports.

## Enforcement

The answer model emits a `premises` array when the question contains a material asserted or presupposed proposition. SUPPORTED and CONTRADICTED premises require exact evidence IDs. UNRESOLVED premises must have no evidence IDs and force an overall status of PARTIAL or NOT_IN_SRD.

The independent auditor receives the original question and must certify both each premise classification and `premise_coverage_complete`. Omitting a material premise therefore fails closed even if all ordinary answer claims are otherwise supported.

## Backward compatibility

Ordinary direct questions use `premises: []`. Existing claim validation, Retrieval v2, answer-unit coverage, SRD source binding, JSON-constrained llama.cpp output, and fail-closed behavior remain in force.
