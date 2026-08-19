---
name: archie-character-create
description: Guides a player through creating an SRD 5.2.1 character and stores explicitly chosen character facts in human-readable YAML. Use when starting a new character, choosing SRD classes/species/background options, or building a level-1 character.
---
# Archie Character Creation

Use `python -m archie.cli ask` for every rule or option question during creation. Never offer an option as an SRD option unless the evidence-gated engine verifies it.

Store completed player facts under `data/characters/<safe-name>.yaml`, using `data/characters/example-ranger.yaml` as the structural example. Do not copy rules text into the character file. The YAML is a record of the player's selections and statistics, not a rulebook.

When a requested option cannot be verified from SRD 5.2.1, explain that Archie cannot verify that option from this source and do not invent its mechanics.
