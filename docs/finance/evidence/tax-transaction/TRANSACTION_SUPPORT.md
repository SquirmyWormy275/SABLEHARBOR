# Current industrial transaction and tax support

These files reproduce the accepted industrial financial generator at base `8898d2d0310a60bdf0e4753036790c6eda1388cd`; they are separate from the immutable operations release and must not be added as new transactions. [Source hashes and full PPA](CURRENT_SOURCE_BRIDGE.json) identify every input and generated schedule. [Native mirror](transaction-support.sqlite3) contains the same CSV populations.

| Schedule | Scope |
|---|---|
| [PPA](acquisition_ppa.csv) | Stock price, book/tax goodwill, net assets, cash and funding bridge |
| [Opening trial balance](aru_acquisition_opening_trial_balance.csv) | Complete acquisition opening accounts |
| [Tax rollforward](aru_2026_tax_rollforward.csv) | All twelve modeled months; tax basis, expense and cash stay distinct |
| [Debt](aru_2026_debt.csv) | Complete 2026 term/revolver/lease schedule |
| [Assets](aru_2026_assets.csv) | Complete 2026 owned/leased depreciation schedule |

The generator asserts sources equal uses, stock consideration less identifiable net assets equals book goodwill, and modeled AGUB less other tax bases equals tax goodwill. No balancing plugs are added. Book goodwill is $14,762,500; separately computed tax goodwill is $13,000,000. The $587,500 reserve DTA and initial $1,762,500 book/tax goodwill component retain the source's conditional accounting treatment.

ARU-CL-07 is filing-ready as of March 2 2026, not evidence of IRS filing/acceptance. The joint election remains a documentary condition. The modeled tax rate, basis and deductions are scenario assumptions, not a tax opinion. ARU's $3M escrow is included in $48M stock consideration. Red Wash's $3M escrow and $0.5M holdback are included in its separate $28M price.

The legal lane identified inconsistent Red Wash pre-close day dates across summaries and instruments; accepted close date and price agree. This schedule preserves that discrepancy without choosing a date. The later accepted Northern Nevada $3M land purchase belongs to separate runtime canon; its unresolved settlement is not imported as an assumed cash payment or vendor liability.
