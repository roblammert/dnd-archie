---
name: archie-character-help
description: Provides player-facing help using an existing local character YAML together with SRD-grounded rules. Use for how a character feature works, what options the character has, or explaining a character sheet.
---


# Archie Character Help

Use the character-aware evidence-gated engine:
```bash
python -m archie.cli ask "<question about this character>" --character data/characters/<name>.yaml
```

Do not infer missing character features from pretrained knowledge. If the character file lacks a needed fact, state what is missing. If a class/feature rule is not retrieved, do not fill it from memory.
