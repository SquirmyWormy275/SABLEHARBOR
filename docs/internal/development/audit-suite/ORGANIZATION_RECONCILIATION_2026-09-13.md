# Audit-suite organization bridge and reconciliation proposal

**Implementation update:** The proposal below is retained as the pre-reconciliation design record. The [dated appointment decision](../../../canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md), structured roster, v1.2.0 vector successor and versioned workforce bridge now implement the dependency edits on this branch. Acceptance into controlling canon remains pending. The source projection has 59 current employee identities plus seven directors, with the fifteen additions explicitly distinguished from the pre-change accepted population.

The submitted audit-suite handover delegates fictional role completion and enterprise reconciliation. This branch implements a source-pinned bridge for every one of the 166 native controls, 54 source-model account records and ten financial processes. It preserves accepted identities separately from proposed occupants and run-specific assignment overlays. These proposals have **not** been accepted into controlling canon, and no Board ratification is asserted.

The proposal JSON in this directory defines fifteen missing named occupants: ten existing organization offices plus five existing support-function roles needed for controllership, facilities, procurement, data/records and environmental governance. Stable `AS-P` identifiers keep these candidates distinct from accepted `P` identities. The effective date is September 13, 2026. No earlier hire or appointment is inferred. Historical scenarios need explicit period-appropriate overlays; new proposed people cannot sign earlier records.

## Existing identity and independence

Accepted sources contain 44 current named employees and seven nonemployee directors. The source population also preserves former employee Rachel Kim; she is not eligible as a current simulated owner. The chart contains duplicate displays for Daniel Mercer and Priya Raman, not duplicate employees. Original names, joining-year qualifications, external/former status and source evidence remain intact.

The bridge reuses product, delivery, research and industrial people within their documented functions. ARU controller Tessa Rourke is not reassigned as corporate CFO. Current J2 leaders are not assigned as independent audit reviewers. Internal Audit’s proposed occupant remains in a separate function reporting to the Board Audit & Compliance Committee. A committee contact cannot exercise a collective committee’s reserved authority alone. Source owner-role labels and approval requirements remain on each control assignment.

A resolved assignment in this module means a complete **proposed named coordination/custody/review route**, not accepted operational delegation, professional certification or proof that the same person performs every local control. Site/business implementation boundaries must be bound when scoping the scenario. The bridge never silently turns the full enterprise catalog into 166 deployed Reno/Boise controls.

## Reconciliation totals and assumptions

| Item | Before | Proposed projection | Interpretation |
|---|---:|---:|---|
| Accepted current named employees | 44 | 44 | Accepted source unchanged |
| Additional named candidates | 0 | 15 | Proposed identities, not fifteen established incremental hires |
| Named directors outside employment | 7 | 7 | Never added to payroll |
| J2 authorized billets | 237 | 237 | No added billets or reassignment of J2 into assurance |
| ESS conditional 2027 occupied/authorized | 48/54 | 48/54 | Thirteen proposed names alias thirteen occupied model positions |
| Internal Audit conditional 2027 occupied/authorized | 8/10 | 8/10 | One proposed name aliases one occupied model position |
| Advisory conditional 2027 occupied/authorized | 32/36 | 32/36 | One proposed name aliases one occupied common-bench position |
| Incremental conditional 2027 FTE/payroll | — | 0 / $0 | Naming assumption, not a hiring forecast change |
| Actual 2026 headcount/payroll delta | Unknown | Unknown | Source data does not establish a full payroll census |
| Newly assigned occupied physical seats | 0 | 0 | No actual workplace assignment asserted |
| Sacramento modeled workplace capacity | 362 | 362 | Proposed capacity remains distinct from occupancy |

Group-level annual loaded costs are taken directly from `enterprise/business/source/policy.json`: ESS $140,000, Internal Audit $150,000 and Advisory $155,000 per modeled occupied position. These are existing synthetic 2027 model assumptions, not researched salaries or individual employment terms. The named slots carry $1,820,000, $150,000 and $155,000 respectively **within** existing group totals. Adding those amounts again would double count payroll. Exact proposed position aliases are exported per person; they do not mutate `BusinessModel.make_roster()`.

Per-control workload FTE remains null because assigning the same person to several controls does not establish hours or fractional staffing. Actual facilities occupancy and employment dates remain null. No candidate is seated in an unbuilt campus or proposed runtime facility. Incremental hiring, cost or seat needs discovered during later reconciliation require an explicit revised proposal rather than invented zero actual costs.

## Concrete dependency edits before canonical adoption

1. Add a dated decision under `docs/canon/` recording the delegated fictional appointments, their effective dates, source assumptions, scope and actual acceptance state. Preserve unrelated OPEN executive-title and J2 personnel questions.
2. Reconcile the relevant role sources in `docs/governance/` through separately versioned successors where a finance lock pins existing bytes. Corporate Secretary, CFO, General Counsel and Internal Audit appointments require their existing authority boundaries; do not fabricate signed board minutes.
3. Update `docs/organization/source/chartbook.json` with approved people/roles/source references, then produce a reviewed successor visual master PDF and generated chart pages. The existing PDF, PNG/SVG output, chart IDs and historical v1.0.0 publication must not be silently replaced by generic artwork.
4. Regenerate `geospatial/facilities/population/{REGISTER.json,BRIDGE.md,DISCREPANCY_REPORT.json}` from the current accepted sources. Increase named coverage only on acceptance; leave actual total employment unknown unless separately established.
5. If forecast identity aliases are adopted, add a separately versioned workforce identity bridge to `enterprise/business/` and reconcile its 2027–2031 output. Preserve occupied/authorized counts, payroll, leave/transfer events and immutable release inputs. A genuine incremental hire instead requires pro-rata payroll, cash and forecast changes.
6. Record explicit person/site/workplace status in the facility population source. Assign no occupied seat until its premises and operating status are established. Any changed program must reconcile `SPACE_REGISTER.json`, `PROGRAM.md`, runtime seat allocations and affected current visual derivatives.
7. Publish the accepted role/control assignment bridge without changing stable CCF control or role IDs. Bind local performers, reviewers, delegation limits, source systems and periods separately from this enterprise contact proposal.
8. Regenerate controlled publications, institutional catalog, wiki/readers and maps as applicable. Run maintainer-mandated governance, organization, publication, finance source-lock, facilities and regression checks. Preserve original approved logos, historical releases and private evaluation boundaries.

At the proposal stage, the shared source/publication edits above had not been performed. They are now implemented on this branch as recorded in the implementation update and dated appointment decision. The API preserves the distinction between this branch projection and accepted controlling canon; implementation does not imply Board ratification or owner visual acceptance.

## Financial training relationships

The bridge reads account constants without executing either financial generator: 23 successor model accounts from `enterprise/business/model.py` and 31 historical-calibration accounts from `src/sable_harbor/generation.py`. Model-qualified IDs prevent the two `1000` cash accounts from being merged as one dataset. Source codes and account types remain exact; financial values are not generated or treated as observed company results.

Authored account/process routes connect those accounts to relevant native control domains. System relationships follow existing control-to-service/component references from `enterprise/services/source/services.json`; no deployed ERP, payroll platform or database instance is invented. Tax is retained as a process even where these charts do not supply a dedicated tax account.

The candidate assertion vocabulary follows PCAOB AS 1105.11–.12. Its five categories support a reference taxonomy; engagement-specific risks determine relevance, and a financial assignment must separately select professional jurisdiction, reporting basis and materiality. The module leaves those selections unset. It does not impose PCAOB rules on every nonissuer, ISA or SOC exercise. [PCAOB AS 1105](https://pcaobus.org/oversight/standards/auditing-standards/details/AS1105).

Research inspection notes and exact source-status qualifications belong in ignored `enterprise/generated/audit-suite/build`; no hidden scenario truth is present in this public-safe proposal or module.
