# Archie v2.0.0-alpha.1

Archie is a local, evidence-gated D&D player assistant. v2.0.0-alpha.1 introduces the **Source Library foundation** while preserving the frozen v1.6 trust engine.

The only enabled rules authority in this alpha remains the locally pinned **System Reference Document 5.2.1**. Gemma's pretrained D&D knowledge is not a rules authority.

## Bootstrap

```bash
./scripts/bootstrap.sh
source .venv/bin/activate
python -m archie.cli doctor
```

## Source Library

```bash
python -m archie.cli sources list
python -m archie.cli sources show srd521
python -m archie.cli sources verify
```

## Retrieval and answers

```bash
python -m archie.cli search "advantage"
python -m archie.cli diagnose-retrieval "What does Prone do?"
python -m archie.cli ask "What happens when I have Advantage?"
```

## Release checks

```bash
./scripts/release_check.sh
./scripts/run_regression.sh
./scripts/run_epistemic_regression.sh
```

See `docs/SOURCE_LIBRARY_ALPHA1.md` for the alpha.1 architecture and guarantees.
