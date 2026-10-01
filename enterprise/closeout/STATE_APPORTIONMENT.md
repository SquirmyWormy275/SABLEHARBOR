# State receipt apportionment — company closeout

Status: implemented, pending repository acceptance. Newly authored market and territory precision is identified in `source/state_apportionment.json`; no election, filing, payment or tax journal is created by this provider.

## Contract

`state_apportionment.build(result, forecast_result, anchor)` returns 288 annual member rows: three scenarios × six years (2026–2031) × (five members in CA, IL and WV, plus separate SHI in PA). Supply company legal `journal_rows`, native industrial forecast `journal_rows`, and `industrial.planning.enterprise.load_anchor()`. The default SHI population comes from `receipt_markets.allocate`; optional precomputed `market_rows` must be that allocator's output from the same legal edition. It is an integration input, not an alternative market-fact authority.

The provider rejects changed pinned industrial sources, changed contract identities/segments, duplicate or missing monthly revenue, wrong periods/entities, duplicate market rows, unmatched legal/native industrial totals and unsupported additional transport territory. Its 29-contract territory population contains 17 transport and 12 storage/terminal contracts. Current territory precision and its conditional forecast continuation preserve Wyoming operations; no new route or carriage authority is created.

SHI service markets and Cradle destination come from the root-owned market source. RWH mineral sales are Illinois receipts of PS, its tax owner. The separate September title-retained toll-conversion custody event creates no sale. Intercompany revenue is excluded from combined denominators; separate SHI Pennsylvania includes its intercompany receipts, whose authored customer benefit is outside Pennsylvania. Employees working in Pennsylvania do not establish a Pennsylvania customer market.

For ARU/BST January 2026, the authored ordinary daily earning convention removes one of 25 book-owned days from the new-target tax population (24/25 retained). January 7 old-target receipts remain in `oldtarget_january7_receipts_excluded_usd`. Acquisition, financing and one-time closing entries require their actual event dates and are outside this revenue convention. Full 2026 annual outputs include conditional September–December; they are not completed August returns.

## Methods and authority

California uses the single-sales method for this finite population. The qualified-activity screen includes mine extraction and Cradle mineral processing. A share above 50% rejects calculation because property/payroll inputs for the alternate method would be needed. See [Schedule R instructions](https://www.ftb.ca.gov/forms/2025/2025-100r-instructions.html). No additional nonoperating gross-receipt population is silently assumed.

Illinois transport subgroup conversion is member transport numerator divided by subgroup transport denominator, rounded to six decimals, multiplied by subgroup total everywhere receipts. Converted sales enter the combined denominator/factor allocation; nontaxable-member Illinois sales are redistributed to taxable members under the documented Finnigan method. Example: transport numerators 5/8, denominators25/175 and all receipts300/700 produce converted25/40. See [Schedule UB/Subgroup instructions, R-03/26](https://tax.illinois.gov/content/dam/soi/en/web/tax/forms/incometax/documents/currentyear/business/miscellaneous/schedule-ub-subgroup-instr.pdf) and [86 Ill.100.3450](https://www.ilga.gov/ftp/JCAR/AdminCode/086/086001000M34500R.html). Selected Wyoming-only transport produces zero Illinois transport numerator, but the nonzero conversion is independently tested.

West Virginia uses the post-2022 market/destination rules in [11-24-7(e)](https://code.wvlegislature.gov/11-24-7/). Pennsylvania's customer delivery rule is supported by [Information Notice Corporation Taxes2014-01](https://www.pa.gov/content/dam/copapwp-pagov/en/revenue/documents/taxlawpoliciesbulletinsnotices/informationalnotices/documents/info_notice_ct_2014-01.pdf). Version and research date are retained in the source authority register. Conditional future-year calculations apply this researched law baseline and require refresh upon a relevant change.

## Reperformance

`python -m pytest -q tests/closeout/test_state_apportionment.py`: 10 passed. Includes nonzero subgroup conversion, Finnigan allocation, California threshold rejection and seven corrupt-population cases. Ruff E4/E7/E9/F/I and `git diff --check` passed.

Actual finance CSV input hashes and results are in `state_apportionment_reperformance.json`. The base2026 denominator is $208,931,989.20; CA SHI numerator $130,010,020.50 (factor0.622260004310), IL PS $36,475,000 (0.174578340730), WV SHI $289,979.50 (0.001387913364), PA SHI zero. Excluded January7 receipts are ARU $61,037.12 and BST $36,535.68. Maximum qualified-activity share across all18 scenario-years is approximately27.156742%.

This is a receipt-factor workpaper. Finance must separately reconcile taxable bases, member losses, tax attributes, minimum taxes, deferred taxes and provision journals. It does not certify a filed return or group election. Precision workpapers retain source cents; actual return rounding is a separate preparation step.
