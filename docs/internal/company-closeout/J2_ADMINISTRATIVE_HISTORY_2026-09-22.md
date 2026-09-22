# J2 administrative appointment history — September 22, 2026

**State:** Reviewable successor, pending acceptance. **Scope:** Issue #19 current-office administrative history, not a new establishment or personnel-design decision.

## What is completed

The September 10 accepted roster fixes six identities, offices and company joining years. The accepted August company census separately contains **181 occupied J2 billets within 237 authorized billets**; its 56 vacancies are authored August population facts, not inferred from unnamed people. The source's January/August office dates below are newly authored fictional history under the company-closeout delegation, not recovered records or dates inferred from joining years.

The new source `enterprise/operations/source/j2_administrative_history_2026_09_22.json` records current-office appointments for Jonathan Goldstryker, Amanda Chenahot, Mara Hammer, Anika Trish, Grant Kohrs and Brett Calder on **January 5, 2026**, acknowledgement January 6, HR registration January 7, and current-incumbency confirmation September 10. These dates establish the current-office administrative episode only; they do not assert an earlier title, initial commission, J2 founding date, uninterrupted service since joining, or the historical absence of another office-holder. They are not recovered board or bank evidence.

Four administrative records map existing occupied, unnamed employees into existing offices from August 1, acknowledged that day and registered August 3:

| Existing employee ID | Existing office |
|---|---|
| SH-EMP-J2-HQ-0003 | ROLE-39 Chief of Staff |
| SH-EMP-J2-CONTACT-0002 | ROLE-41 Deputy Head of Contact |
| SH-EMP-J2-JUDGMENT-0002 | ROLE-50 Deputy Head of Judgment |
| SH-EMP-J2-ORIENTATION-0002 | ROLE-55 Deputy Head of Orientation |

These are anonymous stable IDs already counted and paid once in the accepted population. They receive no new name, employee record, remuneration, reporting power or governance right. Their effective dates are newly authored administrative history, not a claim that census opening dates previously proved appointment. The four *personal names* remain OPEN. Current office authority remains the accepted doctrine, not a power supplied by this source. The authoring authority is the closeout's delegated fictional completion; source acceptance still requires the repository process.

## Precise history still unfulfilled

Issue #19's actual remaining promises are the four personal names, other genuinely needed named occupants, detailed personal biographies and earlier appointment/commission histories. The completed administrative records narrow that issue; they do not fulfill those promises by renaming a census.

Orientation office appointment is distinct from the original professional commission. Grant's and the deputy's original commission start, apprenticeship/Admissions Council evidence, and renewal state remain unrecorded. These facts govern standard six-year tenure, normal eight-year renewal limit, exceptional ten-year cap and permanent later line-role restrictions in the accepted profession doctrine. This successor does not invent a commission start or extension, waive entry requirements, or claim a complete qualified commissioning population. The other 16 occupied Orientation positions likewise lack a completed historical commission register. That is the exact affected qualification/tenure claim, not a blocker for current payroll, named leadership identity or company funding books. A bounded subsequent commission-history source must reconcile that population and preserve existing restrictions; no universal biography project is required for financial inspection.

No new age, degree, former employer, ethnicity, family relationship or discarded name is introduced. Company joining years remain their accepted year precision; exact hire dates are not fabricated as a by-product of this administrative task.

## Reperformance and availability

Run `python -m enterprise.operations.j2_administrative_history --output /tmp/j2-history.json` and `python -m pytest -q enterprise/operations/tests/test_j2_administrative_history.py` in the supported environment. The validator joins the actual roster, exact ten incumbencies and source hashes, rejects duplicates/omissions, wrong named identity/joining year, new powers/payroll, invented anonymous names, inverted dates and office-to-commission promotion. Eleven focused tests passed; Ruff and `git diff --check` passed. An initial unpacking error was corrected to the existing four-value roster API before the passing run.

Actual known-on availability uses the later of September 22's authored day and the source HEAD commit timestamp. Dirty previews are nonpublishable. Historical event dates do not make these new records discoverable before their source existed. A clean source commit remains reviewable, not self-accepted controlling canon. The old September 10 structured source and frozen v1.0.0 company package remain unchanged.
