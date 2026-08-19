---
name: archie-search
description: Searches and diagnoses exact local SRD 5.2.1 evidence without using pretrained D&D knowledge. Use when locating a rule or inspecting retrieval quality.
---

# Archie SRD Search

For ordinary source lookup:
```bash
python -m archie.cli search "<query>"
```

For retrieval debugging:
```bash
python -m archie.cli diagnose-retrieval "<question>"
```

Summarize only what returned SRD evidence establishes. Preserve evidence IDs and PDF page references. Do not browse the web for rules answers.
