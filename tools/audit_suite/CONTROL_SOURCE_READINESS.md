# Control-source readiness implementation gaps

The latest explicit inventory, `source-readiness-maintained-2026-09-14/run-v4-lifecycle/`,
adds the separately collected lifecycle-b branch to reference-v4. It verifies 532
originals and retained copies: 367 documentary and 165 qualified activity versions,
with explicit activity references for 24 of 70 controls. The other 46 have none in
this selection. Eleven source components and two separate audit snapshots are
combined for inspection only; this does not create a coherent company year or
alter reference-v4's own 520-original collection. Earlier inventories below preserve
their original selections and counts.

The maintained [explicit-config inventory](../../docs/internal/development/audit-suite/AQ_SOURCE_READINESS_INVENTORY_2026-09-14.md)
covers the current 70-control corporate SOC 2 + HIPAA scope. Its reference-v3 run
verifies 457 original source versions and retained copies across 115 systems:
359 migrated documents, eight repository documents and 90 qualified activity records.
The documentary sources have unknown
business event dates and provisional custody, not established operating history.

The later eight-component inventory explicitly adds one change branch and its
dependent configuration branch, and selects their two existing collection audits.
It verifies 478 unique source versions and 482 retained instances across three
engagements; four extra retained instances are census copies of existing originals.
Seventeen scoped controls have explicit activity references: IAM-003/IAM-007,
INC-001 through INC-004, TRN-001/TRN-002, BCM-002/BCM-003,
ENG-001/002/003/004/006 and CFG-001/002. This is a reference inventory, not an
applicability or effectiveness determination. The other 53 controls have no explicit
activity reference in this selection. Existing sources elsewhere may still require
reconciliation. The 1,015
OperatingModel versions remain unmapped company-source candidates; their month/model
qualifications and lack of automatic corporate SOC 2/HIPAA applicability are preserved.
Separate branches are not combined into a single company history.

The newest reference-v4 selection has ten components and one fresh collection
engagement: 520 originals across 146 systems, comprising 367 documentary and 153
qualified activity versions. All native/retained hashes and 815 history events were
verified. It adds SEC-002 and TPR-001/002/004 to the explicit activity references,
for 21 of 70 scoped controls; 49 lack such references in this selection. Provider
records address pre-operating internal diligence/review queues, with third-party
support still absent. This does not convert either source counts or control labels
into period coverage, reliability acceptance or professional sufficiency.

The latest paired training collection retains 29 originals and the paired backup
collection retains 51. Both are bounded local exercises, not accepted policy, real
employment/training, deployed infrastructure or full-year population coverage.

Concrete next source families should follow each public control's actual evidence
expectation and procedure, for example:

- BCM-002/003: extend the bounded backup/restore slice only after defining the
  intended system population, period and applicable recovery requirements.
- ENG-002/004: extend the implemented local change/release exercise only after
  selecting its supported system population and period. Its paired Engine rehearsal
  retained 32 originals. Downstream configuration checks retained 12 originals with
  exact upstream pins; neither exercise is included automatically in reference-v3's
  selected inventory or establishes deployed infrastructure.
- TPR-001/002/004: vendor population and tier decisions, due diligence records and
  dated monitoring results, preserving selected-provider versus actual-service status.
- TRN-001/002: extend the local three-role training cycle only after defining the
  intended worker population, onboarding/course changes and required period.
- REC-002: explicit extract query, parameters, timezone, transformations and source
  population reconciliation for each intended test.

These are proposed implementations derived from public control text, not invented
company facts or claims that every mentioned source is absent. Each needs an explicit
source owner, stable record/version identity, time/availability rules and a scoped
collection query before procedure-specific testing. Control references, interval
labels, collected files and administrative completion do not establish population
completeness or period coverage. Human testing, workpaper review and professional
applicability assessment remain separate.

The private MATRIX.json contains all 70 controls, exact source-version identities and
hashes, declared periods/qualifiers, recorded collection receipts, stored procedure/test/
review metadata and per-control proposed source requirements. Unlinked recorded work
is retained separately rather than assigned to a control by inference. The inventory
uses read-only per-database snapshots; it is not a globally atomic or exhaustive census
of every historical workspace. No source, grant, audit work or conclusion is changed.
