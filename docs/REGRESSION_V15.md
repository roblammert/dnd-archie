# v1.5 Regression Focus

The v1.1 38-question regression demonstrated strong fail-closed behavior but exposed retrieval gaps and one audit-coverage risk.

v1.5 specifically targets:

- glossary conditions retrieving incidental monster/spell mentions instead of definitions;
- Concentration retrieving item/spell mentions instead of the general glossary rule;
- spell save DC and Passive Perception formulas;
- informal player language such as "armor number";
- multi-concept questions such as ability check vs saving throw;
- action definitions such as Help;
- false-premise questions such as Invisible targeting;
- cross-page rule continuity;
- player-facing answer statements that are not represented in `claims[]`.

The safety objective remains asymmetric: false refusal is preferable to unsupported rule invention, but v1.5 reduces unnecessary refusals by improving retrieval rather than relaxing the evidence contract.
