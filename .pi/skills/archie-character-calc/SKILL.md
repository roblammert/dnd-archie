---
name: archie-character-calc
description: Performs character-aware D&D calculations by combining a YAML character file with rules retrieved from SRD 5.2.1. Use for AC, passive checks, attack modifiers, spell DCs, HP questions, initiative, and similar calculations.
---


# Archie Character Calculation

Character files must live under `data/characters/`.

Run:
```bash
python -m archie.cli ask "<calculation question>" --character data/characters/<name>.yaml
```

Treat YAML as character facts only. The formula/rule must come from SRD evidence. Arithmetic and logical combinations should be labeled DERIVED by the answer engine. Never let a character note override a rule.
