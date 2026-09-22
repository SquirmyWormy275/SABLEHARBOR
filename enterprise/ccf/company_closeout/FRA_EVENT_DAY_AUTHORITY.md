# FRA event-day authority closeout

Prepared September15,2026 UTC; pending repository acceptance. This successor
resolves the narrow primary-source residual for the fourteen existing rail cases.
It does not enlarge the railway engineering or historical filing population.

## Recovered original notices

| Year | FRA publication update | Effective threshold | Archived capture |
|---|---|---|---|
| 2021 | December22,2020 | $10,700 through January7; $11,200 from January8 | June12,2021 |
| 2023 | November16,2022 | $11,500 from January1 | October2,2023 |
| 2025 | November29,2024 | $12,400 from January1 | November16,2025 |

These are recovered agency publications, obtained through archived copies of the
FRA website. Their exact raw bytes are retained as nonexecuting `.html.txt` files
in `authority_snapshots/`. `rail_authority_review.json` supplies original and
archive URLs, publisher dates, capture timestamps, access date and SHA256 hashes.
A capture date does not become the original publication date or an earlier
availability date for newly authored company records.

The original2025 notice replaces the former inference from the2026 increase.
The2021 transition is now executable in `threshold_on`; the October2021 case
remains above its applicable threshold. The2023 crossing case remains reportable
as a crossing despite repair cost below the equipment threshold.

[2021 original FRA notice, archived](https://web.archive.org/web/20210612233940id_/https://railroads.dot.gov/forms-guides-publications/guides/monetary-threshold-notice),
[2023 original FRA notice, archived](https://web.archive.org/web/20231002151607id_/https://railroads.dot.gov/safety-data/forms-guides-publications/guides/monetary-threshold-notice),
[2025 original FRA notice, archived](https://web.archive.org/web/20251116171657id_/https://railroads.dot.gov/safety-data/forms-guides-publications/guides/monetary-threshold-notice).

## Amendment and event-date review

The Federal Register structured Part225 index returned33 documents published
from2013 through the September15,2026 research cutoff. The review records each
publication's type, effective date, source URL/body hash and scope disposition.
The2010 baseline amendment, effective June1,2011, precedes every selected event.
Later annual CFR text is a cross-check, not authority applied backward merely
because it is convenient. The specific changes to225.19 thresholds are tied to
their effective intervals. No reviewed intervening amendment changes the selected
225.9 immediate-notification or225.11 monthly30-day criteria.

The review separately distinguishes:

- December2016 electronic submission address changes from filing timeliness.
- Civil-penalty changes from accident reporting thresholds.
- The2024–2025 investigation-policy sequence from a claim that FRA actually
  investigated any synthetic case.
- July2025 proposals from enacted rules. Electronic establishment posting became
  an option May28,2026 with access/training conditions; no such performance is
  inferred from this review.
- September30,2026 form-retirement and miscellaneous amendments from the earlier
  edition cutoff. The later15-calendar-day initial-record rule and changed late
  report submission method do not apply to the August14 case or2021 late report.

The fourteen source dates and groups are individually joined in the review.
Results remain eight timely modeled event submissions, one late submission,
five no-trigger cases and eleven incident-form records. The disputed $600,000
claim remains open; it is not rail-repair cost or a proved indemnity recovery.
No real regulator submission or acknowledgement is asserted.

## Validation and reproduction

```sh
python -m enterprise.ccf.company_closeout.rail_authority
python -m enterprise.ccf.company_closeout.rail_reporting
python -m pytest -q enterprise/ccf/company_closeout/test_rail_authority.py enterprise/ccf/company_closeout/test_rail_reporting.py
```

Eight focused tests passed, including changed snapshot, wrong threshold, omitted
event, proposal promotion and premature future-rule application. Actual2021
January transition is checked. The two validators report three original notices,
33 indexed documents, fourteen events and two preserved future-effective rules.
The exact CCF workflow lint and `git diff --check` pass on the source revision.

Initial broad searches and some archive endpoints failed or returned empty
availability responses. Later exact availability queries and raw-capture fetches
succeeded. These failed retrieval attempts are retained in the structured review;
no inaccessible-source claim remains for the three requested notices.
