# Third-party services — executable implementation record

**PR:** #112  
**Reviewed main:** `d17f9838f972e76843714f73f4054cf1c189b763`  
**Input PR head:** `c1d4abc15dfad3ec7a7286bb923bf51f09157de0`  
**Scope:** Authorized registers, workload/recovery proposals, architecture economics, staffing/capacity bridge and tests.

## Delivered implementation

The [enterprise services package](../../../enterprise/services/README.md) contains 57 services, 49 support components, 49 external-dependency requirements, four source-named external counterparties and all six hosting classes. Sourcing is traced to the decision record; source facts, owner decisions, synthetic assumptions and unknown operating capability are separately labeled.

The model implements monthly 2027–2031 comparison for four architecture alternatives plus a staged ownership case; explicit CPU/memory/storage/GPU/rack/power capacity; relief-aware staffing and shared allocations; SaaS input lines; hardware expansion and 48-month refresh; next-month depreciation; operating/capital cash and net book value; 45 demand/price sensitivity results; and a non-destructive bridge to existing financial assumptions. It generates JSON, CSV, a report, checksums and a relational SQLite view.

The initial source data is intentionally not a populated vendor master: KGM, Demotte, Northstar and the synthetic Union Pacific interface retain their source roles. Other providers remain unidentified requirements. The ARU/Red Wash relationship remains internal. No contract, vendor, individual, parcel, rack or occupied staff is invented.

## Reconciliation safeguards

Finance, People & Culture, Procurement, Legal, CISO, Technology, J2 and independent Internal Audit retain their existing authority. Product engineering and Atlas staffing are not transferred to a shared pool. Shared data engineering does not give J2 authority over Finance or customer sources. Education's design billets are not added to J2 twice.

The model records the existing $216,000 annual generic vendor allowance, $1,140,000 corporate facilities allowance and $6,720,000 ESS payroll separately. Detailed requirements do not silently stack onto, or erase, those amounts. Verified reuse and displaced expense remain explicit missing inputs; approved net incremental funding remains null. Contract-input compute exposure is not mistaken for generated/booked expense.

## Validation evidence and limits

Forty-three targeted tests passed in the isolated implementation workspace before initial publication. They cover source/ID/owner boundaries, six-class scope, bidirectional dependencies, historic-party misuse, false operation/approval claims, shared allocation, numeric input errors, capacity headroom, full recovery storage, no duplicated backup population, relief staffing, asset refresh/depreciation/cash reconciliation, staged transitions, SQLite foreign keys, output reproducibility and missing-source failures.

Repository source-byte/CCF/site validation and the broader repository checks run in the accompanying GitHub Actions workflow, against the actual checkout. Local targeted tests alone are not described as full-repository validation. The workflow checks the committed comparison against regeneration and uploads full model outputs as a build artifact. Its run and PR check results supply execution evidence; this file does not predict their outcome.

No deployment, procurement, hiring, SLA acceptance, geographic closeout, controlled-publication release or main-branch merge is claimed. The completed object is a working planning and reconciliation implementation, not an operating data center.
