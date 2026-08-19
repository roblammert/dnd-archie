---
name: archie-equipment-help
description: Compares SRD weapons, armor, adventuring gear, and equipment choices using verified SRD facts plus optional character YAML. Use when a player asks what equipment does, which verified option fits their character, or how equipment changes a calculation.
---
# Archie Equipment Help

For factual properties and mechanics, use:
```bash
python -m archie.cli ask "<equipment question>" --character data/characters/<name>.yaml
```
when character context matters.

Recommendations may use ordinary reasoning, but every mechanical premise supporting the recommendation must be SRD-grounded. Clearly distinguish recommendation from rule.
