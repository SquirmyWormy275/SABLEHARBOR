# CCF baseline design and workflow delivery

The approved corporate/Reno/Boise reference now has authored baseline design analysis and executable proposed procedures. This is a proving ground for the enterprise CCF, not a change to the broader goal of SOC 2/HIPAA baseline controls with selectable framework deltas.

## Delivered design

- 149 baseline requirement analyses: 38 selected TSC criteria, nine description criteria and 102 HIPAA sections.
- 64 distinct proposed native-control procedures with record locations, evidence outputs, reviewer-role descriptions, native ownership/trigger bindings and boundary responsibilities.
- Five concrete supplements for authentication, cryptography/transfers, physical safeguards, capacity and environmental resilience.
- Nine-part service-description workpaper, eight candidate data flows and 192 operating-input rows.
- Mapping analysis identifying uncovered aspects; source paragraph and guidance-candidate locators remain available for independent review.
- Five fictional assessment stages demonstrate corporate evidence reuse, site validation, distinct framework testing, C5 deltas and remediation without erasing history.

Use `python -m enterprise.ccf.assurance.preparation build --source-root ... --output ...` and the matching `verify` command. Start at the generated `START_HERE.md`. The generator and authored inputs live under [enterprise/ccf/assurance](../../../enterprise/ccf/assurance/README.md).

## C5 correction from the Atlas research

Atlas revision `96bda5ef06a1e8b3469704c55b71ff2aae05e830` supplied the publisher's machine-readable ZIP and flagged 29 omitted sharpened subcriteria. This delivery independently reconciled the publisher YAML/PDF identifier sets: 623 children (462 basic, 29 sharpened, 132 complementary) across 168 parents. Two internal gates remain separate from publisher requirements. The source validator rechecks child text hashes, parent/child populations and categories against the pinned ZIP. Old delivered bundles remain unchanged and require their original implementation revision to reproduce.

The corrected reference has 2,322 requirement/boundary rows, all unresolved. The correction improves population completeness; it does not approve mappings or finish the six general conditions and assessment context.

## Acceptance boundaries

The baseline source analysis is authored, not independently accepted. HIPAA section treatment distinguishes direct candidate duties, customer support, reserved/definitional/enforcement context and conditional processes. Paragraph semantics, legal applicability, source currency, guidance relevance and mapping sufficiency still need appropriate review. HHS's court-status overlay is retained; printed source text alone does not establish enforceability. ISO/IEC 27001/42001 full text remains an access dependency, despite the newly acquired 27001 amendment in Atlas's controlled local holdings.

The real reference has no executed tests, operating evidence, appointments or fabricated reviews. Fictional reviews are limited to the original exercise catalog. The same-period failed result stays visible after a passing retest; prospective support is limited to the new one-day fictional period and retains the previous failed test and finding.

Actual service facts, data flows, contracts, system instances, accepted objectives/thresholds, authorized personnel and the examination period are required for operationalization. Deployment, spending, contractual commitments and customer claims are not approved by this design work. Existing material-decision packets remain separate.

## Validation

All 147 CCF tests passed, including design-population omission, cross-boundary evidence misuse, additional-framework test gaps, failed-test preservation, prospective remediation and C5 source omission/category regressions. The source-backed package built and re-performed exactly. Browser checks passed for all five fictional explorers and the 2,799-attribute reference explorer, including the restored sharpened-criterion filter; no JavaScript errors occurred. Governance, hygiene and reader regeneration passed (979 indexed files, 2,194 local links).
