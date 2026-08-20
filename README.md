# Archie v2.0.0-alpha.6

Archie is a local, evidence-gated D&D player assistant. SRD 5.2.1 is its one rules authority; Gemma pretrained D&D knowledge is never rules evidence.

Archie retrieves from four pinned representations of that authority: the official WotC PDF, Open5e SRD-2024, Foundry SRD 5.2, and Cantilux dnd-srd-json. Equivalent representations do not vote or strengthen a claim by repetition. Ambiguous identities are quarantined, and conflicting claims fail closed without hiding unrelated clear facts. Player-facing provenance reports `Authority: SRD 5.2.1`.

Every new D&D rules-fact question handled through Pi is grounded with current Archie retrieval, even if a related fact appeared earlier in the conversation.

## Bootstrap

```bash
./scripts/bootstrap.sh
source .venv/bin/activate
python -m archie.cli doctor
python -m archie.cli ingest
```

## Ask and inspect

```bash
python -m archie.cli ask "What classes can cast Fireball?"
python -m archie.cli search "Fireball" --top-k 5
python -m archie.cli diagnose-retrieval "What does Prone do?"
python -m archie.cli sources list
python -m archie.cli sources verify
```

The CLI prints evidence-backed claims, the evidence actually cited, and the single SRD authority. Import, approval, and enablement remain separate source lifecycle states.

## Release checks

Release work uses the repository virtual environment and committed pinned artifacts; deterministic checks require neither network access nor a live model.

```bash
source .venv/bin/activate
./scripts/release_check.sh
```

See `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md`, and `docs/VALIDATION.md` for developer details.
