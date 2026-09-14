# Control-source readiness implementation gaps

The private September 14 inventory covers the current 70-control corporate SOC 2 +
HIPAA scope. All 359 migrated documentary originals have exact retained collection
copies in the isolated rehearsal. These remain documentary sources with unknown
business event dates and provisional custody, not established operating history.

The inspected independent company stores contain explicit native control references
for six scoped controls: IAM-003/IAM-007 and INC-001 through INC-004. This is a
reference inventory, not an applicability or effectiveness determination. The other
64 controls have no explicit independent-source control reference in these inspected
stores. Existing sources elsewhere may still require reconciliation. The 1,015
OperatingModel versions remain unmapped company-source candidates; their month/model
qualifications and lack of automatic corporate SOC 2/HIPAA applicability are preserved.
Separate branches are not combined into a single company history.

Concrete next source families should follow each public control's actual evidence
expectation and procedure, for example:

- BCM-002/003: dated backup execution and restore-test results tied to critical
  system inventory and the applicable recovery requirements.
- ENG-002/004: approved change/peer-review records linked to exact release artifacts
  and attributable deployment events.
- TPR-001/002/004: vendor population and tier decisions, due diligence records and
  dated monitoring results, preserving selected-provider versus actual-service status.
- TRN-001/002: role-based required-course matrix and dated completion/overdue records
  with an independently reconcilable worker population.
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
