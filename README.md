# Archie v2.0.0-alpha.4

Archie is a local, evidence-gated D&D player assistant. Alpha.4 adds **explicit source approval and authority-aware multi-source retrieval** while preserving the frozen v1.6 fail-closed trust engine.

## Trust model

A source must be **imported**, **approved**, **licensed**, and **enabled** before its evidence may enter retrieval. These states are intentionally separate. The canonical `srd521` PDF remains the highest-priority `official_srd` source. Open5e `srd-2024` is an `approved_supplement` and starts disabled after every import.

Gemma pretrained D&D knowledge remains non-authoritative.

## Bootstrap

```bash
./scripts/bootstrap.sh
source .venv/bin/activate
python -m archie.cli doctor
```

## Source workflow

```bash
python -m archie.cli sources discover open5e
python -m archie.cli sources import open5e srd-2024
python -m archie.cli sources show open5e:srd-2024
```

Import does not grant authority. After independently reviewing the source license, explicitly approve it:

```bash
python -m archie.cli sources approve open5e:srd-2024 \
  --license-name "<verified license name>" \
  --license-url "<verified license URL>"
```

Then enable it:

```bash
python -m archie.cli sources enable open5e:srd-2024
python -m archie.cli sources verify
```

Enablement materializes stable, source-aware evidence IDs from the stored structured records. `sources disable` excludes that source from retrieval without deleting its snapshot or evidence.

```bash
python -m archie.cli sources disable open5e:srd-2024
```

## Authority and edition policy

- active edition defaults to `2024` (`ARCHIE_ACTIVE_EDITION=2024`);
- retrieval ignores enabled sources from other editions;
- `official_srd` outranks `approved_supplement` when evidence overlaps;
- conflicting evidence is never merged into a hybrid rule; unresolved conflicts fail closed;
- only approved/licensed/enabled evidence reaches the answer generator and auditor.

Inspect potential structured-source overlaps with:

```bash
python -m archie.cli sources conflicts
```

## Hashes

`source show` distinguishes two hashes for imported Open5e snapshots:

- **Snapshot file SHA-256** — byte hash of the persisted raw JSON file;
- **Canonical content SHA-256** — stable hash of the imported provider payload used for source version identity.

They are intentionally different values.

## Retrieval and answers

```bash
python -m archie.cli search "advantage"
python -m archie.cli diagnose-retrieval "What does Prone do?"
python -m archie.cli ask "What happens when I have Advantage?"
```

Evidence packets now include source ID, authority type, and edition.

## Release checks

```bash
./scripts/release_check.sh
./scripts/run_regression.sh
./scripts/run_epistemic_regression.sh
```

Run the live alpha.4 multi-source acceptance workflow after setting explicit license metadata:

```bash
export ARCHIE_OPEN5E_LICENSE_NAME="<verified license name>"
export ARCHIE_OPEN5E_LICENSE_URL="<verified license URL>"
./scripts/run_multisource_acceptance.sh
```

Alpha.4 does not add the web application. That begins in the v2.0 beta stages after the source/trust layer is accepted.
