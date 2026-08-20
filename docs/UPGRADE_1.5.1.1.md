# Archie v2.0.0-alpha.5.1 — WotC Source Ingestion Bridge

## Purpose

`v2.0.0-alpha.5.1` is a narrowly scoped bridge release between the existing `v2.0.0-alpha.5` baseline and the planned `v2.0.0-alpha.6.x` backend-hardening series.

Its purpose is to establish a clean, reproducible source-ingestion foundation for multiple machine-readable representations of **Wizards of the Coast SRD 5.2.1** without prematurely implementing the authority, deduplication, retrieval, or answer-selection behavior already assigned to alpha.6.

The governing rule for this release is:

> **Wizards of the Coast SRD 5.2.1 is the sole D&D content authority. Open5e SRD-2024, Foundry SRD 5.2, and Cantilux dnd-srd-json are machine-readable representations of that authority, not independent authorities.**

No non-WotC D&D content is permitted into Archie's rules corpus in this release.

---

# 1. Release Boundary

## In scope

Alpha.5.1 may add:

- a formal identity for `wotc:srd-5.2.1`;
- representation-aware source metadata;
- a source manifest;
- reproducible source revision locking;
- an Open5e SRD-2024 importer;
- a Foundry SRD 5.2 importer;
- a Cantilux `dnd-srd-json` importer;
- strict WotC-only provenance filtering;
- raw-source preservation;
- normalization into Archie's existing ingest model;
- deterministic rebuilding;
- fixture and integration tests;
- diagnostic source-ingestion reports;
- documentation necessary to operate and test these capabilities.

## Explicitly out of scope

Alpha.5.1 must **not** implement or redesign:

- final source-authority ranking semantics;
- evidence voting;
- final evidence deduplication;
- canonical evidence selection;
- entity-aware retrieval behavior planned for alpha.6.2;
- authority-minimal evidence selection planned for alpha.6.3;
- conflict-resolution policy planned for alpha.6.3;
- claim minimization planned for alpha.6.4;
- final answer-source semantics;
- API or web work;
- campaign management;
- accounts or sessions;
- unrelated backend features.

If work requires answering the question:

> “Which representation should Archie trust when answering?”

that work belongs in alpha.6, not alpha.5.1.

Alpha.5.1 should instead answer:

> “What authority does this record belong to, which representation supplied it, and is it allowed into the corpus?”

---

# 2. Git Workflow

Start from the current development branch.

```bash
git switch 2.0.0_dev
git status
git pull --ff-only
```

Before doing anything else, ensure the working tree is clean.

```bash
git status --short
```

Expected:

```text
<no output>
```

Verify that the current baseline is actually alpha.5.

```bash
git log -1 --oneline
git tag --points-at HEAD
```

If `v2.0.0-alpha.5` already exists, do not recreate it.

If the actual alpha.5 release commit is not tagged, identify the correct commit before proceeding and create the release tag there.

Then create the implementation branch:

```bash
git switch -c feature/alpha5.1-wotc-source-ingestion
```

Do all alpha.5.1 work on this branch.

Do not start alpha.6 implementation on this branch.

---

# 3. Versioning

Use:

```text
Git/release version:
v2.0.0-alpha.5.1
```

If the Python package currently uses PEP 440-compatible versions such as:

```text
2.0.0a5
```

use:

```text
2.0.0a5.post1
```

for the package version.

That sorts correctly:

```text
2.0.0a5
<
2.0.0a5.post1
<
2.0.0a6
```

Do not change the project's established versioning convention unless necessary.

The Git release name may remain:

```text
v2.0.0-alpha.5.1
```

even if the Python package metadata uses:

```text
2.0.0a5.post1
```

---

# 4. Required Source Model

Archie must distinguish between:

```text
authority
```

and:

```text
representation
```

## Authority

The content publisher/source whose rules are being represented.

For this release:

```text
wotc:srd-5.2.1
```

is the only permitted D&D authority.

## Representation

The machine-readable form through which Archie acquired the content.

Required representations:

```text
wotc:official-srd-5.2.1
open5e:srd-2024
foundry:srd-5.2
cantilux:dnd-srd-json
```

Conceptually:

```text
Wizards of the Coast
SRD 5.2.1
     │
     ├── Official SRD document
     │
     ├── Open5e structured representation
     │
     ├── Foundry structured representation
     │
     └── Cantilux structured representation
```

All four refer to one authority.

They must never be treated as four independent votes.

---

# 5. Source Manifest

Add a declarative source manifest in the location most consistent with the existing repository.

Suggested path:

```text
config/sources/wotc-srd-5.2.1.yaml
```

Suggested logical structure:

```yaml
schema_version: 1

authority:
  id: wotc:srd-5.2.1
  publisher: Wizards of the Coast LLC
  title: System Reference Document 5.2.1
  ruleset: dnd-5e-2024
  license: CC-BY-4.0

representations:
  - id: wotc:official-srd-5.2.1
    kind: canonical-document
    priority: 100
    authoritative: true

  - id: open5e:srd-2024
    kind: structured
    priority: 90
    authoritative: false
    required_provenance:
      document.key: srd-2024

  - id: foundry:srd-5.2
    kind: structured
    priority: 85
    authoritative: false
    required_provenance:
      sourceBook: SRD 5.2

  - id: cantilux:dnd-srd-json
    kind: structured-document
    priority: 80
    authoritative: false
    derived_from: wotc:srd-5.2.1
```

The `priority` field may be retained as metadata for future use.

Alpha.5.1 must not turn it into final answer-selection policy.

---

# 6. Preserve Compatibility with Current Alpha.5

Do not aggressively replace existing source fields.

If alpha.5 currently contains fields such as:

```text
source_id
source
document_id
```

preserve them unless changing them is unavoidable.

Add the new concepts alongside the existing model:

```text
authority_id
representation_id
```

The migration should be additive wherever possible.

Example:

```yaml
source_id: srd-2024
authority_id: wotc:srd-5.2.1
representation_id: open5e:srd-2024
```

Alpha.6.1 can later decide which legacy fields should become part of the permanent contract.

---

# 7. Representation Adapters

Use a common adapter boundary.

Suggested structure:

```text
src/archie/
└── ingest/
    └── representations/
        ├── __init__.py
        ├── base.py
        ├── open5e_srd2024.py
        ├── foundry_srd52.py
        └── cantilux_srd_json.py
```

Adapt the paths to the existing repository rather than forcing this exact layout.

Each adapter should conceptually support:

```python
load(...)
validate_provenance(...)
normalize(...)
```

Prefer a common protocol or abstract interface if the existing architecture supports it naturally.

Do not perform retrieval ranking inside adapters.

Do not perform final evidence conflict resolution inside adapters.

---

# 8. Open5e Importer

Only accept Open5e objects whose source provenance identifies:

```text
document.key == "srd-2024"
```

Anything else must not enter the WotC corpus.

Examples of expected behavior:

```text
Open5e SRD-2024 monster
→ ACCEPT

Open5e SRD-2024 spell
→ ACCEPT

Open5e Black Flag spell
→ REJECT

Open5e Tome of Heroes feat
→ REJECT

Open5e record with missing provenance
→ INVALID / REJECT
```

The importer should record:

```text
authority_id = wotc:srd-5.2.1
representation_id = open5e:srd-2024
```

Do not infer WotC provenance merely from familiar names.

The explicit source metadata must pass.

---

# 9. Foundry Importer

Only ingest records explicitly attributable to:

```text
SRD 5.2
```

Prefer the actual structured source metadata available in the Foundry source record rather than identifying content solely by pack name.

Expected behavior:

```text
Foundry SRD 5.2 record
→ ACCEPT

Foundry PHB 2024 premium record
→ REJECT

Foundry DMG record
→ REJECT

Foundry MM premium record
→ REJECT

Foundry record without adequate provenance
→ INVALID / REJECT
```

Accepted records receive:

```text
authority_id = wotc:srd-5.2.1
representation_id = foundry:srd-5.2
```

Do not accidentally ingest premium Foundry content.

---

# 10. Cantilux dnd-srd-json Importer

Use the `dnd-srd-json` corpus only when its corpus/version metadata confirms that the representation derives from SRD 5.2.1.

Accepted records receive:

```text
authority_id = wotc:srd-5.2.1
representation_id = cantilux:dnd-srd-json
```

Preserve its useful structural information where it maps cleanly to Archie's existing ingest model:

- documents;
- sections;
- collections;
- resource records;
- structured tables;
- indexes.

Do not redesign Archie's entire entity schema simply to expose every upstream field.

Normalize only what fits the current system cleanly.

Preserve unneeded raw fields in raw observations if useful for later work.

---

# 11. Raw Source Preservation

Preserve downloaded or observed upstream data separately from normalized Archie data.

Conceptual layout:

```text
data/
├── raw/
│   └── wotc-srd-5.2.1/
│       ├── open5e/
│       ├── foundry/
│       └── cantilux/
│
├── normalized/
│   └── wotc-srd-5.2.1/
│
└── manifests/
```

Use the repository's existing data layout if one already exists.

Raw representations should remain immutable for a given pinned upstream revision.

Normalization should be repeatable from raw input.

---

# 12. Do Not Vendor Large Upstream Repositories Unnecessarily

Prefer locking the upstream revision rather than committing entire third-party source repositories into Archie.

Create an appropriate source lock file, for example:

```text
sources.lock
```

Conceptually:

```yaml
schema_version: 1

sources:
  open5e:
    representation_id: open5e:srd-2024
    revision: "<exact commit or immutable version>"

  foundry:
    representation_id: foundry:srd-5.2
    revision: "<exact commit or immutable version>"

  cantilux:
    representation_id: cantilux:dnd-srd-json
    revision: "<exact commit or immutable version>"
```

Record enough information to reproduce the corpus exactly.

Do not use mutable references such as:

```text
main
master
latest
HEAD
```

as the only recorded version.

---

# 13. Deterministic Source Operations

Use existing Archie command conventions if available.

If new commands are necessary, prefer operations conceptually equivalent to:

```bash
archie sources fetch
archie sources verify
archie ingest rebuild
```

Do not invent new CLI commands merely for aesthetic consistency if equivalent commands already exist.

Required behavior:

### Fetch

Acquire the exact pinned representation.

### Verify

Confirm:

- source identity;
- pinned revision;
- required provenance;
- expected files;
- checksums where appropriate;
- WotC-only boundary.

### Rebuild

Normalize the accepted content into Archie's database/index.

Repeated rebuilds against unchanged sources must produce equivalent normalized state.

---

# 14. Source Diagnostics

Each ingest run should produce a useful summary.

Example:

```text
Source: open5e:srd-2024

Observed:               1524
Accepted WotC SRD:       643
Rejected non-WotC:       881
Invalid provenance:        0
Normalization failures:    0

PASS
```

For Foundry:

```text
Source: foundry:srd-5.2

Observed:                982
Accepted WotC SRD:       721
Rejected other content:  261
Invalid provenance:        0
Normalization failures:    0

PASS
```

Exact numbers will depend on upstream data.

Do not make tests depend on brittle exact total counts unless those counts are tied to a pinned source snapshot and intentionally treated as invariants.

The following should fail the operation:

```text
invalid provenance > 0
unexpected authority admitted > 0
normalization failures > 0
unresolved source identity > 0
```

---

# 15. Canonical Entity Identity

Alpha.5.1 should make it possible to recognize that multiple representations may describe the same logical rule entity.

Example:

```text
open5e:srd-2024 → Acid Arrow
foundry:srd-5.2 → Acid Arrow
cantilux:dnd-srd-json → Acid Arrow
```

These should be capable of carrying a common normalized identity such as:

```text
spell:acid-arrow
```

However:

**Do not implement final evidence collapsing or source-selection behavior in alpha.5.1.**

It is sufficient that normalized records can be associated with the same logical identity while retaining their representation provenance.

Final evidence deduplication remains alpha.6.3 work.

---

# 16. Provenance Requirements

Every normalized imported object must be able to answer:

```text
What authority owns this content?
Which representation supplied it?
Which upstream revision supplied it?
What upstream identifier/path supplied it?
When was it normalized?
```

Prefer data equivalent to:

```yaml
authority_id: wotc:srd-5.2.1

representation:
  id: open5e:srd-2024
  revision: abc123...

upstream:
  record_id: ...
  path: ...

normalization:
  schema_version: 1
```

Avoid timestamps in deterministic hashes if they would make repeat builds unnecessarily different.

---

# 17. Testing Requirements

## A. Unit tests

Each representation adapter needs focused tests.

### Open5e

Test:

```text
accepts SRD-2024 record
rejects non-SRD Open5e record
rejects missing document provenance
preserves upstream identity
assigns correct authority_id
assigns correct representation_id
normalizes representative entity types
```

### Foundry

Test:

```text
accepts SRD 5.2 record
rejects non-SRD source
rejects missing provenance
preserves upstream identity
assigns correct authority_id
assigns correct representation_id
```

### Cantilux

Test:

```text
accepts validated SRD 5.2.1 corpus
rejects invalid/mismatched corpus metadata
preserves section/resource identity
assigns correct authority_id
assigns correct representation_id
```

---

# 18. Cross-Representation Tests

Create fixtures representing the same logical entity from more than one representation.

Example:

```text
Acid Arrow
```

Test that:

```text
all accepted records have authority_id = wotc:srd-5.2.1
each retains its own representation_id
each retains its own upstream identity
they can share a canonical entity identity
none overwrites another representation silently
```

Do not test final authority selection yet.

---

# 19. WotC Boundary Tests

These are release-critical.

Create fixtures that deliberately attempt to contaminate the corpus.

Examples:

```text
Open5e third-party monster
Open5e third-party spell
Foundry premium/non-SRD item
Foundry premium/non-SRD class
record with no source attribution
record with ambiguous source attribution
record claiming an unknown authority
```

Every one must be rejected.

Add at least one integration assertion equivalent to:

```text
SELECT DISTINCT authority_id FROM dnd_rules;
```

Expected:

```text
wotc:srd-5.2.1
```

and nothing else.

If the datastore does not support SQL, implement the equivalent assertion.

---

# 20. Determinism Tests

Run the same ingest twice from the same pinned raw sources.

Confirm that the normalized substantive data is identical.

At minimum verify:

```text
entity IDs identical
record counts identical
normalized field values identical
authority IDs identical
representation IDs identical
source revisions identical
```

If practical, compute a deterministic corpus fingerprint.

Example:

```text
normalized_corpus_sha256
```

Two unchanged builds should produce the same fingerprint.

---

# 21. Idempotency Test

Test this sequence:

```text
clean database
→ ingest
→ record corpus state
→ ingest again without deleting anything
→ compare corpus state
```

Expected:

```text
no duplicate logical records
no duplicate source observations unless explicitly designed
no changed canonical identifiers
no changed substantive normalized state
```

This is foundational for alpha.6.5 lifecycle work.

---

# 22. Existing Regression Suite

After the new tests pass, run every test that currently passes on alpha.5.

Alpha.5.1 is not successful if source ingestion works but existing Archie behavior breaks.

Record:

```text
baseline suite:
PASS / FAIL

new alpha.5.1 suite:
PASS / FAIL

integration suite:
PASS / FAIL
```

No known regression should be accepted merely because alpha.6 is coming later.

---

# 23. Release Acceptance Criteria

Alpha.5.1 is releasable only when all of the following are true:

- current alpha.5 tests still pass;
- all three structured representations can be ingested;
- only WotC SRD 5.2.1 content enters the permitted corpus;
- every imported record retains authority provenance;
- every imported record retains representation provenance;
- upstream source revisions are reproducible;
- repeated rebuilds are deterministic;
- repeated ingest is idempotent;
- non-WotC contamination fixtures are rejected;
- no final alpha.6 authority-selection policy has been introduced;
- no unrelated feature work has entered the branch;
- documentation reflects the new source model;
- working tree is clean after the release validation process.

---

# 24. Suggested Commit Sequence

Prefer small reviewable commits.

Suggested sequence:

```text
chore(sources): add WotC SRD 5.2.1 source manifest

feat(provenance): add authority and representation metadata

feat(ingest): add Open5e SRD-2024 representation adapter

feat(ingest): add Foundry SRD 5.2 representation adapter

feat(ingest): add dnd-srd-json representation adapter

feat(ingest): enforce WotC-only source provenance

feat(sources): add pinned source revisions and verification

test(ingest): add representation and WotC boundary fixtures

test(ingest): add deterministic and idempotent rebuild coverage

docs(release): document alpha.5.1 source ingestion

chore(release): prepare v2.0.0-alpha.5.1
```

Do not force these exact commits when existing repository structure suggests a better grouping.

Avoid one massive implementation commit.

---

# 25. Codex Workflow in VSCode

Do **not** begin by telling Codex simply:

```text
Implement alpha.5.1.
```

That gives it too much freedom.

Use several constrained passes.

---

# Codex Prompt 1 — Repository Reconnaissance and Plan

Use this first in planning/ask mode.

```text
We are preparing Archie v2.0.0-alpha.5.1 on the current
feature/alpha5.1-wotc-source-ingestion branch.

Do not modify files yet.

Inspect the repository and produce an implementation plan for a narrowly scoped
bridge release between v2.0.0-alpha.5 and the already-planned alpha.6.x series.

Release mission:

Add a reproducible, representation-aware ingestion foundation for Wizards of
the Coast SRD 5.2.1.

The sole permitted D&D content authority is:

    wotc:srd-5.2.1

Machine-readable representations to support:

    open5e:srd-2024
    foundry:srd-5.2
    cantilux:dnd-srd-json

These are representations of the same WotC authority. They must NOT be modeled
as independent evidentiary authorities.

Important scope boundary:

alpha.5.1 MAY implement:
- authority/representation metadata;
- source manifests;
- source revision locking;
- adapters/importers;
- WotC-only provenance validation;
- normalization;
- raw observation preservation;
- deterministic ingest;
- idempotency;
- tests and diagnostics.

alpha.5.1 MUST NOT implement:
- final authority ranking semantics;
- final evidence deduplication;
- conflict resolution policy;
- entity-aware retrieval changes planned for alpha.6.2;
- authority-minimal evidence selection planned for alpha.6.3;
- claim minimization planned for alpha.6.4;
- answer-generation changes;
- unrelated features.

Before proposing changes:

1. Inspect AGENTS.md and all relevant project governance/development files.
2. Identify the current version declaration and release conventions.
3. Map the current ingest architecture.
4. Identify current source/provenance models.
5. Identify existing source acquisition/rebuild commands.
6. Identify test architecture and release validation scripts.
7. Identify files that should change.
8. Identify files that should deliberately remain unchanged.
9. Call out any compatibility risks with alpha.6.
10. Recommend the smallest implementation that satisfies this release.

Return:

- repository findings;
- proposed file-level changes;
- migration strategy;
- testing plan;
- likely risks;
- explicit alpha.6 scope protections.

Do not write code yet.
```

Review this output yourself.

The plan should match the release boundary in this guide.

If Codex proposes implementing retrieval ranking, conflict resolution, or comprehensive deduplication, reject that part.

---

# Codex Prompt 2 — Foundation and Provenance

Once the plan is acceptable:

```text
Implement only the alpha.5.1 source-model foundation from the approved plan.

Tasks:

1. Add the WotC SRD 5.2.1 authority identity:
       wotc:srd-5.2.1

2. Add representation identities:
       wotc:official-srd-5.2.1
       open5e:srd-2024
       foundry:srd-5.2
       cantilux:dnd-srd-json

3. Add or extend source metadata so normalized records can retain:
       authority_id
       representation_id
       upstream identity
       pinned upstream revision

4. Preserve backward compatibility with the existing alpha.5 source model.
   Prefer additive changes over destructive schema replacement.

5. Add a declarative source manifest for WotC SRD 5.2.1.

6. Add unit tests for the new metadata and manifest behavior.

Do NOT implement representation importers yet.

Do NOT implement alpha.6 authority-selection or retrieval behavior.

Run the smallest relevant test suite after changes.

At completion report:
- files changed;
- compatibility decisions;
- tests executed;
- results;
- any unexpected architecture issues.

Do not broaden scope.
```

Review the diff and commit.

---

# Codex Prompt 3 — Open5e Adapter

```text
Implement the Open5e SRD-2024 representation adapter for alpha.5.1.

Requirements:

- Representation ID:
      open5e:srd-2024

- Authority ID for accepted content:
      wotc:srd-5.2.1

- Only records explicitly attributable to:
      document.key == "srd-2024"
  may enter the WotC corpus.

- Reject records from every other Open5e source.
- Reject or explicitly fail records with missing/invalid provenance.
- Preserve upstream record identity and pinned revision.
- Normalize through the existing Archie ingest architecture rather than
  inventing a parallel storage system.
- Preserve raw observations according to existing repository conventions.
- Add representative unit fixtures.
- Include at least one non-WotC Open5e fixture proving rejection.

Do NOT implement retrieval ranking, evidence voting, final deduplication, or
conflict resolution.

Run relevant tests and report results.
```

Review and commit.

---

# Codex Prompt 4 — Foundry Adapter

```text
Implement the Foundry SRD 5.2 representation adapter for alpha.5.1.

Requirements:

- Representation ID:
      foundry:srd-5.2

- Authority ID for accepted content:
      wotc:srd-5.2.1

- Accept only records whose actual source provenance identifies SRD 5.2.
- Do not rely solely on object names or familiar D&D names.
- Explicitly reject non-SRD and premium rulebook content.
- Preserve upstream object identity, source metadata, and pinned revision.
- Normalize through Archie's existing ingest architecture.
- Add unit fixtures for accepted SRD content.
- Add fixtures proving non-SRD Foundry content is rejected.

Do NOT add premium PHB, DMG, or Monster Manual content.

Do NOT implement alpha.6 authority-selection behavior.

Run relevant tests and report results.
```

Review and commit.

---

# Codex Prompt 5 — Cantilux Adapter

```text
Implement the Cantilux dnd-srd-json representation adapter for alpha.5.1.

Requirements:

- Representation ID:
      cantilux:dnd-srd-json

- Authority ID:
      wotc:srd-5.2.1

- Validate that the selected corpus/version derives from SRD 5.2.1.
- Preserve useful resource/document/section/table identity.
- Normalize only fields that fit Archie's existing ingest model cleanly.
- Do not redesign the entire entity schema merely to mirror upstream JSON.
- Preserve raw source material where appropriate.
- Preserve pinned upstream revision.
- Add tests for accepted corpus metadata.
- Add a test proving mismatched or invalid provenance is rejected.

Do NOT implement alpha.6 retrieval or authority-selection work.

Run relevant tests and report results.
```

Review and commit.

---

# Codex Prompt 6 — Source Locking and Determinism

```text
Complete the reproducibility portion of alpha.5.1.

Implement the smallest mechanism consistent with this repository that:

1. Pins the exact upstream revision/version for each structured representation.
2. Makes source identity inspectable.
3. Detects an unexpected or changed source.
4. Supports deterministic rebuild from unchanged pinned input.
5. Avoids requiring large third-party repositories to be committed into
   Archie's repository unless the current architecture specifically requires it.

Add tests for:
- source revision validation;
- deterministic rebuild;
- repeated rebuild equivalence;
- idempotent ingest;
- changed/mismatched source detection.

If commands equivalent to sources fetch / sources verify / ingest rebuild
already exist, extend them instead of adding redundant commands.

If no such mechanism exists, add only the minimum interface necessary.

Do not perform unrelated CLI redesign.

Run all relevant tests and report results.
```

Review and commit.

---

# Codex Prompt 7 — WotC Boundary Integration Test

```text
Add alpha.5.1 release-critical integration tests for the WotC-only corpus
boundary.

The finished D&D rules corpus for this release must contain only:

    authority_id == "wotc:srd-5.2.1"

Test deliberate contamination attempts including:

- Open5e third-party content;
- Foundry non-SRD content;
- unknown authority IDs;
- missing source provenance;
- ambiguous source provenance.

All must be prevented from entering the permitted WotC corpus.

Also test that multiple accepted representations of the same logical entity:

- retain one WotC authority identity;
- retain distinct representation identities;
- retain distinct upstream provenance;
- can share a normalized logical entity identity;
- are not silently overwritten.

Do NOT implement final evidence collapsing or source voting. Those remain
alpha.6.3 work.

Run the integration tests and report the exact results.
```

Review and commit.

---

# Codex Prompt 8 — Full Regression and Scope Audit

Do this before release preparation.

```text
Perform a release-readiness audit for Archie v2.0.0-alpha.5.1.

Do not add features during this pass.

1. Run the complete existing alpha.5 regression suite.
2. Run all new alpha.5.1 tests.
3. Run repository integration/acceptance/release scripts that apply.
4. Check deterministic rebuild behavior.
5. Check idempotent ingest behavior.
6. Confirm the D&D corpus contains no authority other than:
       wotc:srd-5.2.1
7. Search the alpha.5.1 diff for accidental implementation of planned
   alpha.6 functionality, specifically:
   - final source ranking;
   - final evidence deduplication;
   - conflict resolution;
   - entity-aware retrieval redesign;
   - claim minimization;
   - answer-generation changes.
8. Check for generated files, downloaded upstream repositories, temporary
   artifacts, secrets, or caches that should not be committed.
9. Check git status.
10. Produce a release-readiness report.

Do not fix unrelated pre-existing issues.

If a release-blocking alpha.5.1 defect is found, identify it clearly before
making any correction.
```

If Codex finds a real release blocker, fix only that blocker.

---

# Codex Prompt 9 — Release Documentation and Version Bump

Once everything passes:

```text
Prepare Archie v2.0.0-alpha.5.1 for release.

Do not change application behavior during this task.

1. Update the project version using the repository's established versioning
   convention.
2. Add/update the changelog.
3. Document the authority-vs-representation model.
4. Document the supported representations:
       open5e:srd-2024
       foundry:srd-5.2
       cantilux:dnd-srd-json
5. Document the WotC-only restriction.
6. State explicitly that final authority selection, evidence deduplication,
   conflict resolution, retrieval hardening, and answer minimization remain
   alpha.6 work.
7. Update any release checklist required by this repository.
8. Run the release validation tests again.
9. Report every changed file and final test result.

Do not commit or tag automatically unless repository instructions explicitly
authorize that behavior.
```

---

# 26. Manual Review Before Merge

Run:

```bash
git status
git diff 2.0.0_dev...HEAD --stat
git diff 2.0.0_dev...HEAD
```

Review specifically for:

- unexpected dependency changes;
- unrelated refactoring;
- non-WotC data;
- large vendored source trees;
- generated databases;
- changed retrieval semantics;
- changed answer behavior;
- removed alpha.5 compatibility paths;
- alpha.6 code appearing early.

Then run your normal complete test suite manually if Codex's execution environment differs from your real local environment.

---

# 27. Merge

When the branch is clean and all acceptance criteria pass:

```bash
git switch 2.0.0_dev
git pull --ff-only
git merge --no-ff feature/alpha5.1-wotc-source-ingestion \
  -m "Merge v2.0.0-alpha.5.1 WotC source ingestion foundation"
```

Run the release validation again **after the merge**.

Do not assume branch tests guarantee the merge result.

---

# 28. Tag

When post-merge validation passes:

```bash
git tag -a v2.0.0-alpha.5.1 \
  -m "Archie v2.0.0-alpha.5.1 - WotC source ingestion foundation"
```

Verify:

```bash
git show v2.0.0-alpha.5.1 --stat
```

Then push:

```bash
git push origin 2.0.0_dev
git push origin v2.0.0-alpha.5.1
```

Delete the feature branch only after the tag and remote development branch are verified.

```bash
git branch -d feature/alpha5.1-wotc-source-ingestion
```

If you also maintain remote feature branches:

```bash
git push origin --delete feature/alpha5.1-wotc-source-ingestion
```

---

# 29. Changelog Entry

Use wording equivalent to:

```markdown
## v2.0.0-alpha.5.1

### Added

- Representation-aware provenance for SRD ingestion.
- Explicit WotC SRD 5.2.1 authority identity.
- Open5e SRD-2024 structured representation support.
- Foundry SRD 5.2 structured representation support.
- Cantilux dnd-srd-json representation support.
- Strict provenance filtering preventing non-WotC content from entering the
  D&D rules corpus.
- Reproducible source revision locking and verification.
- Deterministic and idempotent source-ingestion validation.

### Changed

- Source metadata can now distinguish authoritative content origin from the
  machine-readable representation supplying the record.

### Deferred to alpha.6

The following remain intentionally unchanged:

- retrieval authority semantics;
- final evidence deduplication;
- conflict resolution;
- claim minimization;
- answer-generation source selection;
- public API behavior.
```

---

# 30. Final Release Validation Record

Record at minimum:

```text
Archie Release Validation

Release:
v2.0.0-alpha.5.1

Base:
v2.0.0-alpha.5

Branch:
2.0.0_dev

Authority:
wotc:srd-5.2.1

Representations:
- open5e:srd-2024
- foundry:srd-5.2
- cantilux:dnd-srd-json

Existing regression suite:
PASS / FAIL

New unit tests:
PASS / FAIL

Integration tests:
PASS / FAIL

WotC boundary:
PASS / FAIL

Deterministic rebuild:
PASS / FAIL

Idempotent ingest:
PASS / FAIL

Repository clean:
PASS / FAIL

Non-WotC authority records:
0

Unresolved provenance records:
0

Alpha.6 scope audit:
PASS / FAIL

Release decision:
PASS / FAIL
```

---

# 31. Alpha.6 Handoff

After alpha.5.1 is merged, alpha.6 should inherit the new ingestion infrastructure rather than reopen its design.

The planned sequence remains:

```text
v2.0.0-alpha.6.1
Contracts & taxonomy

v2.0.0-alpha.6.2
Entity-aware retrieval

v2.0.0-alpha.6.3
Authority & deduplication

v2.0.0-alpha.6.4
Answer minimization

v2.0.0-alpha.6.5
Lifecycle & operational hardening

v2.0.0-alpha.6.6
Backend freeze validation
```

Alpha.5.1 establishes:

```text
WHAT IS THIS CONTENT?
WHOSE CONTENT IS IT?
WHICH REPRESENTATION SUPPLIED IT?
IS IT ALLOWED?
CAN WE REPRODUCE IT?
```

Alpha.6 will establish:

```text
HOW SHOULD IT BE RETRIEVED?
HOW SHOULD DUPLICATES BE COLLAPSED?
HOW ARE CONFLICTS RESOLVED?
WHAT EVIDENCE IS SUFFICIENT?
WHAT SHOULD THE USER ACTUALLY SEE?
```

That boundary should remain intact throughout implementation.

---

# Definition of Done

`v2.0.0-alpha.5.1` is complete when Archie can reproducibly ingest the permitted SRD 5.2.1 representations, prove that every resulting D&D record belongs to the WotC SRD 5.2.1 authority, preserve where each representation came from, reject non-WotC contamination, rebuild deterministically and idempotently, pass all previous alpha.5 regressions, and do all of that **without prematurely implementing alpha.6's retrieval and authority-resolution behavior**.