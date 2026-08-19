---
name: archie-explain
description: Explains an SRD-grounded D&D rule in beginner-friendly language while preserving evidence provenance. Use when the user asks to explain, teach, simplify, give an analogy, or explain like they are a child/new player.
---


# Archie Explain

Use the strict answer engine with the teaching request included in the question:
```bash
python -m archie.cli ask "Explain <rule/question> for a beginner using a simple example."
```

The SRD supplies mechanics. The model may create analogies, examples, and simpler wording, but may not introduce a new mechanic that lacks evidence.
