# Portable SOC 2 audit-program pilot

This is a source-bound training exercise over the two alternative fictional 2027
company histories already in this Git repository. It selects three candidate
procedures from the existing audit program: vulnerability coverage (CC7.1),
security baseline/publisher reconciliation (SEC005 TOE, candidate CC6.6/CC6.8),
and recovery timing (A1.3). The [frozen plan](PLAN.json) states boundary,
period, frequency, population, sample, procedure, exception rule, evidence and
review limits. Its mappings remain candidates. This exercise does not issue a
SOC 2 report or establish all year operating effectiveness.

## Run from another machine

Clone the public repository from GitHub and record the commit. The entire company
source delivery is in Git; no workstation service, local SQLite database or
credential is needed for the exercise. Python dependencies are in `pyproject.toml`.

```sh
git clone https://github.com/SquirmyWormy275/SABLEHARBOR.git
cd SABLEHARBOR
git rev-parse HEAD
uv sync
uv run python -m tools.audit_suite.company_record_delivery verify --root docs/audit-suite/company-records
uv run python -m tools.audit_suite.soc_program_pilot init submission.json
```

`init` verifies the full 5,714-version delivery and writes a new submission with
the exact selected source inventory: 39 versions for `history-01`, 55 for
`history-02`. It refuses to overwrite an existing submission. Work through each
history separately. The public [intake guide](../CLEAN_MESSY_INTAKE.md) describes
the histories; the grader never infers outcomes from their names.

For each of the six task/history cells in `submission.json`:

1. Use the source inventory paths to open actual company originals. Distinguish
   `event_at`, `available_at` and `imported_at` and cite each relied-on source as
   `{"path": "history-01/...json", "sha256": "<inventory hash>"}`. The selected
   source versions for each task are checked by the CLI. Cite both exercise versions
   when a history contains both, and retain later corrections as separate versions.
2. Fill every typed `observations` field. IDs and omitted assets are sorted JSON
   arrays; `count_contradictions` is an integer; monthly reconciliations are
   objects keyed by `YYYY-MM`; recovery minutes and within-target decisions are
   arrays in exercise version order. Use `LIMITATION` for a selected documentary
   method that has not completed the authored control or live/restore procedure.
3. Write the finding and the retest/scope note. Identify the preparer and record
   a review of scope and limitations. An asserted reviewer identity is retained
   as an assertion; the CLI does not authenticate that person.

```sh
uv run python -m tools.audit_suite.soc_program_pilot check submission.json
```

The public check verifies exact source and plan pins, all answers present,
history separation, citation hashes, and the complete selected task source sets. It gives no
answer key. Keep the completed submission and the Git commit used to produce it.

## Grade after submission

An owner-authorized independent system can clone the **private**
`SquirmyWormy275/SABLEHARBOR-ALEXANDRIA-CONTROL` repository after completing the
exercise. Its `alexandria_workbench.soc_audit_grader` command holds the private
expected outcomes and the scripted grade/replay workflow. See its
`docs/soc-program-pilot/README.md`. Access to that private repository requires
the owner's GitHub entitlement; the key is deliberately absent here. An
independent system with both repositories can grade itself locally without a
workstation-specific service or network call after cloning.

The grade checks 40 typed observations and emits exact citation lineage,
source-method results, submitted and expected values, and explicit limitations.
Its review kind is `SCRIPTED_ENGINEERING`; human professional review is a
separate decision. The rest of the audit backlog, full enterprise populations,
system description, actual scanner/network enforcement, backup restore and
independent data usability remain untested in this bounded pilot.
