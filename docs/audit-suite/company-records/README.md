# Complete retained company records

These are the actual retained synthetic company records, included directly in Git. An ordinary clone contains **all 11,198 source versions across 1,424 source systems**: the 5,714 versions and 922 systems of the recovered source-only company snapshot, plus 5,484 later authored versions in 502 systems, declared as eleven authored extensions. Open the JSON, text and binary files directly; no local launcher, external drive, credentials or generator is needed.

The [data availability record](../DATA_AVAILABILITY.md) explains publication and recovery. The narrower [November client submissions](../demo-2026-11/client-records/README.md) provide a ready-to-use exercise with correspondence and walkthroughs. This directory supplies the broader company source history behind that kind of work.

| History | Native source branch | Source versions | Systems | Complete source provenance |
| --- | --- | ---: | ---: | --- |
| [History 01](history-01/) | HARBOR-OPERATIONS-A | 5,556 | 698 | [provenance.jsonl](history-01/provenance.jsonl) |
| [History 02](history-02/) | HARBOR-OPERATIONS-B | 5,642 | 726 | [provenance.jsonl](history-02/provenance.jsonl) |

The histories are separate alternatives. Preserve the branch, system, record and version when joining records; do not add the two histories together as one company population. The [manifest](manifest.json) lists every file and preserves each original identity, source version, business-event time, availability time, import time, origin, source hash and delivery hash. Its systems register also retains every source owner. Each provenance line joins on the same five identity fields and retains the complete source provenance, ingestion command identifier and input digest. In particular, qualification, completeness, authority, control mappings and source relationships remain available.

For audit-software testing, [the CLEAN/MESSY intake guide](../CLEAN_MESSY_INTAKE.md)
maps History 01 to CLEAN and History 02 to MESSY and explains how to import one
verified history at a time while retaining native identities and dates.

Of the 11,198 files, **11,193 retain their exact original bytes**. Five are explicitly marked derivatives: only absolute workstation `source_root` or `runtime_root` values were replaced with consistent `local-source:` locators. Their original hashes and changed JSON field paths remain in the manifest. No source facts, record versions or historical errors were removed. The file extensions reflect the retained source media types: 11,180 JSON files, 12 small binary source objects and six text files.

## Authored additions after the recovered snapshot

The manifest `snapshot` keeps the recovered database hash and size together with `base_source_version_count` (5,714) and `base_source_system_count` (922). Each later addition is declared in `snapshot.authored_extensions` with its import time, origin, input sources, systems, version count and the hash of the manifest it extends; the verifier checks that declaration against the delivered records.

`WORKPLACE-CAPACITY-2027-V1` (imported 6 November 2026, origin `AUTHORED_TRAINING_SOURCE`) adds `workplace-history.capacity_register`, `workplace-history.workplace_assignment` and `workplace-history.headcount_capacity_bridge` to each history: 23 versions in History 01 and 16 in History 02. They reconcile each history's own named affiliation register to the planning desk capacity in [`geospatial/facilities/SPACE_REGISTER.json`](../../../geospatial/facilities/SPACE_REGISTER.json). Capacity is planning capacity, assignment is not attendance, and open, conflicting, provisional and not-evaluated items are recorded as such in each history. Each history records its own assignments, timing and exceptions; do not combine them.

Ten further extensions, imported together on 6 November 2026 with the same origin, add the company's 2027 operating record. Each is a linked documentary trail: requests, approvals, third-party documents, receipts, system logs and the general-ledger postings in `finance-history.journal_entry` that cite them.

| Extension | What it adds | History 01 | History 02 |
| --- | --- | ---: | ---: |
| `SHARED-MASTER-2027-V1` | Vendor onboarding, tax-ID and bank-detail verification, vendor and carrier masters, chart of accounts, cost centers and the 2027 close calendar | 352 | 366 |
| `FACILITIES-SECURITY-2027-V1` | Seat requests, work tickets, badges, visitor and escort logs, after-hours exceptions and access removal | 339 | 320 |
| `PERMITTING-ENVIRONMENT-2027-V1` | Building permits, plan review, inspections and hearings; environmental packets for Red Wash, the rail corridor and Cradle; cultural-resource clearance and tribal consultation; asset-retirement estimates | 169 | 172 |
| `LOGISTICS-OPERATIONS-2027-V1` | Transport orders, waybills, bills of lading, scale tickets, proof of delivery, freight invoices, assays, quality holds, production logs, mass balances and inventory counts | 272 | 278 |
| `CLOSE-ESTIMATES-2027-V1` | Subsequent-event packs, period cut-off populations, an allowance-estimate revision chain, identity resolution and request-list submissions | 211 | 208 |
| `CRM-CUSTOMERS-2027-V1` | Opportunities, quotes, activities, customer onboarding and credit, exemption certificates, invoices, receipts, dunning, support tickets and service credits | 259 | 256 |
| `TRAVEL-EXPENSE-2027-V1` | Corporate cards and statements, travel requests, expense reports with receipts, petty cash and office-supply purchasing | 297 | 293 |
| `PAYROLL-HR-2027-V1` | Payroll registers, timesheets, funding, tax deposits and filings, payroll-to-ledger reconciliation, credentials, background checks, leave, separations and prevailing-wage reports | 306 | 299 |
| `TRADE-COMPLIANCE-2027-V1` | Classification, restricted-party screening, foreign-person and visit records, licences, technology control plans, export determinations and training | 270 | 265 |
| `GOVERNANCE-COMPLIANCE-2027-V1` | Insurance, retirement-plan administration, product-safety declarations, continuity tests, vendor risk, tax provision, grants, ethics cases, legal holds and master-data changes | 265 | 248 |

The two histories share natural keys such as person, vendor, account and site identifiers, but each records its own completeness, timing and exceptions. Open, conflicting, provisional and not-evaluated items stay explicit in the records.

These are fictional company records and local reference exercises. Their own provenance and scope limitations remain authoritative; possession of a record does not establish real employment, deployment, compliance, or audit sufficiency. Source chronology is retained, including records with future fictional dates. This snapshot is complete for the two populated source tables (`systems` and `versions`), not a claim that every possible company fact was ever authored. Evaluator packages and live workspace authentication are separate from company evidence.

From the repository root, verify the complete delivered population with standard Python:

```sh
python3 -m tools.audit_suite.company_record_delivery verify --root docs/audit-suite/company-records
```

Verification checks every member, source/delivery relationship, provenance digest, system membership and count. It reports 11,198 versions, 1,424 systems, 11,193 originals and five derivatives. It does not need the original private database. The manifest is a checksum inventory, not an independent signature; retain the Git commit when citing this edition.
