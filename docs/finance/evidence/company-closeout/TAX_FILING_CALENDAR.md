# Entity filing calendar and performance boundary

Recorded September 15, 2026. `tax_filing_register.csv` is generated from
`enterprise/closeout/tax_calendar.py`; each row has entity, tax year, legal/tax
classification, instrument, due date, preparation, modeled submission,
acknowledgement, source authority and evidence state. Calendar-year scope only.

US/California corporate returns use April 15 next year, adjusted for weekends
and the District of Columbia Emancipation Day holiday. The calendar explicitly
handles the 2019-year July 15, 2020 pandemic postponement. Pennsylvania current
RCT-101 due dates use the 15th of the following month. Delaware LLC annual tax
remains June 1, corporate annual report March 1; Wyoming reports remain first
day of formation-anniversary month. No unsupported business-day extension is
applied to the online Delaware/Wyoming administrative due dates.

Authorities actually reviewed September 15, 2026:

- [2017 IRS Form 1120 instructions](https://www.irs.gov/pub/irs-prior/i1120--2017.pdf),
  [current Form 1120 instructions](https://www.irs.gov/instructions/i1120), and
  [Notice 2020-23](https://www.irs.gov/pub/irs-drop/n-20-23.pdf).
- [2016 California corporation instructions](https://www.ftb.ca.gov/forms/2016/16_100bk.pdf)
  and [2025 instructions](https://www.ftb.ca.gov/forms/2025/2025-100-booklet.html).
- [2025 Pennsylvania CT-1 instructions](https://www.pa.gov/content/dam/copapwp-pagov/en/revenue/documents/formsandpublications/formsforbusinesses/corporationtax/documents/2025/2025_rev-1200.pdf).
- [Delaware annual tax instructions](https://corp.delaware.gov/paytaxes/),
  [Wyoming anniversary instructions](https://sos.wyo.gov/Forms/WyoBiz/What%27s_Next.pdf)
  and [Wyoming asset worksheet](https://sos.wyo.gov/forms/business/general/arworksheet.pdf).
- [IRS Form 8023 instructions](https://www.irs.gov/instructions/i8023): January 7,
  2026 acquisition gives October 15, 2026 intended-election deadline. Preparation
  is distinct from joint signature/submission; no filing is inferred.

SHI federal 2016–2025 and early California 2016–2023 modeled electronic submissions
are newly authored March preparation/April submission events consistent with the
historical workpaper. They are not recovered government acknowledgements. Later
California combined-report work remains `NOT_RUN_MISSING_FILING_EVIDENCE`; future
returns remain `FUTURE_DUE`. No future observation is used as evidence known in
August 2026. This calendar uses September 15 authorship throughout.

The early SHI April submission dates precede potential 2023 California storm
relief, so they do not depend on that relief. The due-date field is the ordinary
calendar (apart from the explicit nationwide pandemic override); it must not be
used to assert a late-filing violation without checking taxpayer-specific relief.
[IRS October 16, 2023 official bulletin](https://content.govdelivery.com/accounts/USIRS/bulletins/3761181)
provides November 16 relief for eligible California storm taxpayers. No filing
in this register is treated as late by ignoring that extension.

This register covers represented income/entity tax duties, not payroll/excise,
sales-tax or all local filings. RWH remains in PS's income return while keeping
its own legal/operator/employment duties. ARU pre-close S and BST QSub conditional
states are preserved; their post-close C returns do not by themselves establish
a federal consolidated return. Pennsylvania site nexus and California unitary
membership are examined separately from formation jurisdiction.

Residuals are explicit: Pennsylvania historical form-version review and actual
factor/provision joins; Delaware share/asset franchise-tax calculations; Wyoming
asset-situs license calculations; subsidiary current return reconciliations; and
California combined-report work. Missing filing evidence is not represented as
submitted, not-applicable, or a completed control. The calendar is reviewable
implementation and does not alone close the full enterprise tax gate.
