# Orientation commission history — September 22, 2026

**Document ID:** SH-OO-COMMISSIONS-2026-09-22. **State:** Reviewable successor pending repository acceptance. **Scope:** The 18 occupied Orientation positions in the accepted August company census, within 24 authorized positions. No new names, people, payroll, powers, tenure extension or waiver.

## Completed history

`enterprise/operations/source/orientation_commissions_2026_09_22.json` supplies **newly authored fictional history**, under the closeout's ordinary-completion delegation. It does not claim recovered historical files or infer commissioning from company joining years. On acceptance it supplies the bounded original-commission detail previously left open in the September 22 administrative appointment memo; that memo's six accepted identities, office dates and remaining biography scope are unchanged.

The 18 existing employee/position IDs are arranged in six three-person selected cohorts, commissioned February 2 of 2021–2026. Each has three distinct recommendation perspectives (senior, peer and junior), a reviewed background/prior-work/writing/problem/interview packet, six-day Assessment and Selection, approximately one year of supervised apprenticeship with four reviews, a subsequent Admissions Council decision, restrictions acknowledgement, unique numbered pin, and an ordinary six-year commission ending on an exclusive anniversary date. This is the complete admission-history population for these 18 current occupants; it is not a census of all historical applicants or an assertion that no other historical cohort member existed.

Grant Kohrs retains his accepted 2020 company joining year; the new selection starts January 2020, apprenticeship February 2020–January 2021 and commission February 2, 2021. His current Head appointment of January 5, 2026 falls within that term. This does not establish an exact hire date or J2 founding date. His standard term and those of two peers end February 2, 2027; their October 1, 2026 transition reviews are **future-due planned work**, not completed renewal. No eight-year renewal or exceptional ten-year term is used.

The deputy is the existing unnamed employee `SH-EMP-J2-ORIENTATION-0002`; commissioning precedes the authored August office appointment. Historical recommenders, instructors and council members are role-scoped supporting records, not backdated appointments of today's named office-holders or additions to today's payroll. The procedure is authored consistently with current accepted doctrine; it does not claim that the September 2026 published doctrine existed during earlier years.

## Negative case and assignment boundaries

`SH-EMP-J2-ORIENTATION-0012` was not selected in its first November 2022 A&S attempt after overstating confidence under contradictory evidence. The separate January 2023 second attempt passed, followed by apprenticeship and February 2024 commissioning. Both records remain present. This is expressly a **newly authored negative case**, not a claim that a recovered source previously documented failure; nonselection is not a disciplinary mark. The register contains 19 attempts for 18 people, and no third attempt or automatic admission.

Current assignments preserve one Head, one Deputy, four Senior Orientation Officers and 12 Orientation Officers: no junior/associate grade. The Office of CEO and Board have distinct officers; CFO and planning observation are separately identified. The three executive/board-office postings have 24-month planned windows within their existing commissions. Assignments confer observation/orientation only, not line control or a voting board seat. Tests deny pre-commission and post-expiry assignments. Assignment planning cannot extend a commission, and this source does not show a future rotation as already performed.

Permanent later line-executive restrictions, the serving voting-board prohibition, and the five-year post-service nonexecutive cooling/disclosure rule remain exactly as accepted. No eligibility waiver, future director appointment or new governance body is created. Internal July 2026 induction in the company census remains a different record from this professional admission chain.

## Validation, availability and remaining scope

Run:

```sh
python -m enterprise.operations.orientation_commissions --output /tmp/orientation-commissions.json
python -m pytest -q enterprise/operations/tests/test_orientation_commissions.py enterprise/operations/tests/test_j2_administrative_history.py
```

**33 tests passed** (22 commission tests, 11 administrative tests), including entire-population omission/duplication, duplicate pins, missing recommendations/packet elements, too-short apprenticeship, self-review, commissioning before qualification, extension/waiver, restriction loss, expired/prohibited assignments, merged CEO/Board assignments, erased failure and premature known-on visibility. Ruff and `git diff --check` passed.

The source hash population includes current doctrine, accepted identity/census and the administrative successor. Generated availability is the later of the authored September 22 day and the actual HEAD commit timestamp; dirty previews are nonpublishable. The output is reviewable source evidence until repository acceptance, not a self-issued professional opinion. Earlier fictional event dates never make new records available earlier.

This closes the ordinary selected-population commissioning gap on acceptance, including all 18 occupants' standard terms. It does not complete personal biographies, new personal names for anonymous offices, every prior employment episode, all-time unsuccessful-candidate history or evidence for the six vacant positions. Those are distinct issue #19 claims; a new company package must explicitly consume this successor before its frozen exports can be said to contain it.
