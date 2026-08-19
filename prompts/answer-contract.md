# Answer contract — v1.5

The executable contract is in `archie/prompts.py` and enforced by `archie/answer.py`.

A positive rules answer must include a machine-readable claim list. Every claim cites one or more evidence IDs present in the retrieval packet. Python rejects invented evidence IDs.

In strict mode, a second evidence-only pass audits two things:

1. whether each proposed claim is supported by its cited SRD evidence; and
2. whether every factual D&D mechanic stated in the player-facing answer is represented by supported claims.

The second check closes the v1.1 audit-escape class where an unsupported statement could appear in prose while being absent from `claims[]`.

The model may explain facts in new words and invent pedagogical analogies, but those freedoms never create rules authority.
