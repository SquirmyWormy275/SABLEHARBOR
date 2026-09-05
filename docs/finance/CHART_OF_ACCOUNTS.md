# Chart of accounts v0.1

The chart deliberately distinguishes software, services, mining, logistics, recovery, Advisory, intercompany activity, and environmental obligations.

| Range | Class | Implemented examples |
|---|---|---|
| 1000–1699 | Assets | Cash, receivables, mine inventory, PP&E, accumulated depreciation, goodwill/intangibles |
| 2000–2399 | Liabilities | Payables/accruals, debt, asset-retirement obligation |
| 3000–3999 | Equity | Contributed capital and accumulated deficit |
| 4000–4099 | Revenue | Foundry subscription, implementation/support, Atlas, concentrate, freight/terminal, Cradle, Advisory, intercompany |
| 5000–5999 | Direct costs | Cost of revenue and physical production |
| 6000–6399 | Operating expense | R&D, sales/marketing, G&A, depreciation/depletion/accretion |
| 6400–6499 | Intercompany expense | Freight and shared services |
| 9000–9099 | Consolidation | Elimination-only accounts |

Account codes are globally stable; legal entity and segment are dimensions rather than encoded into account numbers. This prevents separate charts from making consolidation and cross-business analysis opaque.

Revenue recognition policies, depletion methods, ARO measurement, PPA useful lives, impairment units, capitalization policies, and tax books remain accounting-policy decisions rather than properties inferred from account names.
