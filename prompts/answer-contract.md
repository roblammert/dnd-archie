# Answer contract

The executable form of this contract is in `archie/prompts.py`.

A valid positive rules answer must contain a machine-readable claim list. Every claim carries one or more evidence IDs that were present in the retrieval packet. Code rejects an answer containing an invented evidence ID. In strict mode, an independent evidence-only model pass audits every claim; any failed or missing audit causes a fail-closed `PARTIAL` response.

The model may explain facts in new words and invent pedagogical analogies. Those freedoms never make the analogy itself a rules authority.
