# J2 personnel completion — September 22, 2026

**Document ID:** SH-J2-PERSONNEL-COMPLETION-20260922. **Repository status:** Pending acceptance. **Intended accepted canon state:** LOCKED for the finite scope below. **Authority:** The owner's current instruction, “OK. Finish everything,” continuing the company-closeout delegation for supported fictional completion. These specific names and career details are implementation selections under that delegation, not separately quoted historical owner selections.

## Decision and exact scope

Adopt the following names for four **existing** occupied employee IDs and existing offices. This supplies missing names; it does not hire people, rename another approved person, create posts or change pay, reporting powers or governance rights.

| Existing person ID | Name | Existing office | Newly authored company joining year |
|---|---|---|---:|
| SH-EMP-J2-HQ-0003 | Miriam Solano | ROLE-39 Chief of Staff | 2019 |
| SH-EMP-J2-CONTACT-0002 | Owen Faraday | ROLE-41 Deputy Head of Contact | 2020 |
| SH-EMP-J2-JUDGMENT-0002 | Nadia Ivers | ROLE-50 Deputy Head of Judgment | 2021 |
| SH-EMP-J2-ORIENTATION-0002 | Leila Soren | ROLE-55 Deputy Head of Orientation | 2019 |

Preserve the six previously approved names, offices and joining years exactly: Jonathan Goldstryker (2020), Amanda Chenahot (2021), Mara Hammer (2021), Anika Trish (2021), Grant Kohrs (2020) and Brett Calder (2021). No discarded proposal or background is revived. Company joining years remain year precision, not exact hire days or founding dates.

Adopt the ten bounded professional biographies, 22 prior-career/function episodes and ten internal role-competency reviews in [the personnel source](../../enterprise/operations/source/j2_personnel_completion_2026_09_22.json). Each biography supplies relevant pre-Sable Harbor experience and the development of that person's work within SHI. External career settings are expressly fictional and are not real third-party confirmations, new group entities or current commercial relationships. No degree, professional license, ethnicity, family tie, age or real employer confirmation is invented.

Internal skills reviews retain a reviewer distinct from the subject, a work sample, source/uncertainty exercise, authority-boundary case and review observation. These are newly authored synthetic internal review records. They do not create hiring/promotion authority for the reviewer or certify external qualifications. Grant and Leila's profiles join their existing accepted Orientation admissions and commissions; their office appointments, commission dates, six-year terms, no-renewal states and professional restrictions remain unchanged. The previously retained unsuccessful A&S case for another officer remains intact.

## Supersession and completion boundary

On accepted merge, this decision supersedes only the following residual claims in issue #19 and their dated source representations: four missing personal names, and missing bounded professional biographies/prior-function histories for the ten current leadership offices. It also expressly disposes of the open-ended “other unnamed occupants where needed” criterion for this declared company scope: the remaining existing staff are sufficiently identified by stable employee IDs for payroll, access, qualifications and operating records. No additional named-person requirement has been identified in the ten-office/18-commission population. No new mandate to name every billet or write hundreds of biographies is created.

The 237 authorized J2 billets, 181 occupied billets and 18 commissioned Orientation occupants remain unchanged. Six vacant Orientation positions are not commissioned. The ten administrative appointment episodes accepted through PR #169 retain their original dates; the 18-person commission source accepted there retains its admission attempts, failures and term limits. Old source files, manifests and released ZIPs remain historical bytes, with their old OPEN labels superseded only within this decision's stated scope.

After source acceptance and integration of these names/history joins into the current edition, there is **no substantive personnel criterion from issue #19 left open within this finite scope**. Exact hire days, private family backgrounds, exhaustive daily careers and all-time unsuccessful-applicant history are explicitly outside this completion claim. This is a bounded disposition, not a claim that every possible fact about each person is documented. Future appointments, expiry reviews and new personnel changes remain ordinary later events.

## Representation and known-on rules

`enterprise.operations.j2_personnel_completion.build(context=None)` produces the ten profiles with source hashes and actual source-commit availability. `join_people(people, known_on=..., context=None)` joins only to existing employee IDs, changing name, current position title and disclosed joining year; it preserves every other person/population/payroll field. It copies inputs, refuses duplicate/missing employees and wrong legal employers, and applies no new history before its actual known-on boundary. Dirty preview data is nonpublishable.

The provider is a successor view, not a competing HR database or a hand edit to a frozen roster. Shared exports, catalogs and source-acceptance manifests require integration-owned regeneration and acceptance. No branch file alone closes issue #19 or retroactively inserts this source into an older released edition.

## Validation

Run:

```sh
python -m enterprise.operations.j2_personnel_completion
python -m pytest -q enterprise/operations/tests/test_j2_personnel_completion.py enterprise/operations/tests/test_j2_administrative_history.py enterprise/operations/tests/test_orientation_commissions.py
```

**51 tests passed**: 18 personnel tests plus 33 prior administrative/commission tests. They verify the complete ten-profile population, four exact name-to-existing-ID joins, six preserved names/years, 702-person unchanged company census, 181 occupied J2 positions, unchanged payroll/access fields, chronological career/commission joins, independent internal review, no external credential claim and actual known-on/dirty-preview denial. Ruff and `git diff --check` passed. No new cash, contribution, compensation, legal entity or voting interest results from this decision.
