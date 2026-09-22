# Independent statutory tax workpaper review

Reviewed September22,2026 UTC (September21 LosAngeles), read-only finance commits64c6e6fe/4c41f333 and corrective6448089e. This is an intermediate helper review, not final composed-journal acceptance or a tax opinion.

Current computation keeps PS, ARU and BST separate federal taxpayers; mine losses do not offset ARU federal profit. State computation combines jurisdiction-specific income, apportions to individual members, and carries member losses separately. The newly authored2025 group precedes ARU/BST acquisition: SHI/SHIH/PS, with104.9M California parent and12.6M Illinois mine receipts. A preapportionment PS loss is not itself an Illinois loss carryforward. No defect was identified in that scope during this review.

California's2024–2026 suspension screen uses member California taxable income before its NOL deduction. Do not import the older2010–2011 aggregate preapportionment threshold. Primary sources read September22: [2024 FTB3805Q instructions](https://www.ftb.ca.gov/forms/2024/2024-3805q-instructions.html), [FTB1061](https://www.ftb.ca.gov/forms/2024/2024-1061-publication.pdf), and [LegalRuling2011-04](https://www.ftb.ca.gov/tax-pros/law/legal-rulings/2011-04.pdf). The latter distinguishes income subject to tax from the old preapportionment test. The2025 ScheduleP100 instructions repeat the current taxable-income exception; the2025Q endpoint was unavailable in this review.

## Finding and correction

The initial deferred helper treated a closing nonland taxable-difference balance as scheduled future reversal capacity and recognized an NOL benefit from80% of it. No actual reversal-year schedule net of overlapping deductible temporary differences supported that capacity. Reserving those other benefits does not eliminate their future deductions. This was communicated to finance before final composition.

Corrective6448089e retains gross DTA/DTL and reserves all deferred benefits under the disclosed management basis until a net reversal schedule supports recognition. ARO/contingency gross benefits remain visible and fully reserved; no future-profit or goodwill-removal deduction was introduced. This resolves the identified recognition defect within that declared basis, without asserting a universal accounting-policy conclusion.

## Reperformance

The source replay supplied by finance was executed independently from its worktree after correction. It emitted54 subsidiary federal current rows,270 state member current rows and342 gross deferred/valuation rows. The six focused current/deferred tests pass. Base2026 federal gross DTA/DTL/full allowance examples: PS10,135,477.9076 /9,155,180.9592 /10,135,477.9076; ARU3,299,807.0463 /3,976,753.2754 /3,299,807.0463. These are intermediate input-dependent results, not pinned final release figures.

Remaining integration checks: apply journals once; reconcile annual provision to current/deferred movements, payment populations and legal/consolidated statements; reperform on the final common source head; retain historical ROT opening correction and all unpaid/filing states. The deferred helper's dictionary inputs currently assume upstream unique member/scenario/year workpapers; standalone duplicate-input guards should be retained or added when exposed as a public import boundary. This review did not certify final export completeness.
