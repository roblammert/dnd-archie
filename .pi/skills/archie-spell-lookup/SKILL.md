---
name: archie-spell-lookup
description: Looks up, explains, and checks use of spells using only SRD 5.2.1 evidence. Use for spell descriptions, casting time, range, components, duration, concentration, targeting, damage, healing, or whether a character can use a spell.
---
# Archie Spell Lookup

Run the strict engine:
```bash
python -m archie.cli ask "<spell question>"
```
Or add `--character data/characters/<name>.yaml` when the answer depends on a specific character.

Do not complete a spell from remembered D&D text if retrieval is partial. Preserve `PARTIAL`/`NOT_IN_SRD` when returned.
