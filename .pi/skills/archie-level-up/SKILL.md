---
name: archie-level-up
description: Guides an existing character through leveling using only SRD 5.2.1 rules and the character's YAML facts. Use when a player gains a level, needs to know what changes, or must make level-up choices.
---
# Archie Level Up

Read the selected YAML in `data/characters/`. Ask the evidence-gated engine what the relevant class level grants:

```bash
python -m archie.cli ask "For this character, what does reaching level <N> change and what choices must the player make?" --character data/characters/<name>.yaml
```

Do not update YAML with an option until the player actually chooses it. Do not infer subclass, feat, spell, or feature rules from memory.
