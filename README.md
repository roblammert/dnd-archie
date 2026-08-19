# Archie v2.0.0-alpha.5

Archie is a local, evidence-gated D&D player assistant. Alpha.5 adds **multi-source answer integration** on top of alpha.4's approved Source Library.

## What changed

Approved Open5e `srd-2024` evidence can now participate in answers with deterministic source provenance. Every answer is classified as:

- `official_only`
- `supplemental_only`
- `mixed`
- `none`

Only sources actually cited by answer claims are reported as used. The official SRD remains higher priority than approved supplements. Exact duplicate evidence is suppressed before generation. Conflicting same-entity structured records fail closed before the LLM is called.

Gemma pretrained D&D knowledge remains non-authoritative.

## Bootstrap

```bash
./scripts/bootstrap.sh
source .venv/bin/activate
python -m archie.cli doctor
```

## Source lifecycle

```bash
python -m archie.cli sources discover open5e
python -m archie.cli sources import open5e srd-2024
python -m archie.cli sources approve open5e:srd-2024 \
  --license-name "<verified license name>" \
  --license-url "<verified license URL>"
python -m archie.cli sources enable open5e:srd-2024
python -m archie.cli sources verify
```

Import, approval, and enablement remain separate states.

## Answers

```bash
python -m archie.cli ask "What classes can cast Fireball?"
```

The CLI prints evidence-backed claims followed by the exact sources actually cited and the answer's authority mode.

## Release checks

```bash
./scripts/release_check.sh
./scripts/run_regression.sh
./scripts/run_epistemic_regression.sh
```

After independently verifying Open5e SRD license metadata:

```bash
export ARCHIE_OPEN5E_LICENSE_NAME="<verified license name>"
export ARCHIE_OPEN5E_LICENSE_URL="<verified license URL>"
./scripts/run_multisource_answer_acceptance.sh
```

See `docs/MULTISOURCE_ANSWER_ALPHA5.md` for the alpha.5 trust contract.

The FastAPI/HTMX web application is not part of alpha.5.
