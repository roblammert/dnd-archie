---
name: archie-rules
description: Answers D&D rules questions using only evidence retrieved from the pinned local SRD 5.2.1 corpus. Use for any question about rules, mechanics, spells, classes, species, feats, equipment, conditions, combat, actions, or game terms.
---


# Archie Rules

For every D&D rules question, including a follow-up that repeats or refers to a fact already discussed, route through the evidence-gated executable in the current turn instead of answering from model or conversation memory. Prior conversation may inform query wording, but it is never evidence for a new factual answer.

```bash
python -m archie.cli ask "<user question>"
```

Return the command's player-facing answer, status, and useful citations. Do not add uncited D&D rules facts afterward. You may clarify wording or add a non-rules analogy if it does not change the mechanic.

If the command fails, report the failure. Never fall back to pretrained D&D knowledge.
