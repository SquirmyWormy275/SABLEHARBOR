# Working accounting policies

**Status: MODEL_PROPOSED; qualified accounting review required. The model is not audited and does not claim GAAP compliance.**

- Calendar year, monthly periods, accrual basis, USD functional/reporting currency; multi-currency columns are present but FX generation is not yet populated.
- Debits and credits are stored as positive Decimal amounts. Each line has exactly one side; each entry and aggregate trial balance must balance.
- Posted entries are immutable. Reversals and replacements correct errors. Closed periods reject new ordinary posting.
- Upfront platform invoices credit contract liabilities; ratable recognition debits the liability and credits revenue. Implementation and milestone policy interfaces require further expansion.
- Collectability and credit-loss estimation are not yet production-grade.
- R&D is expensed in the current base scenario. Capitalized-software alternatives remain scenario work.
- Equipment uses straight-line depreciation in implemented slices. Mine depletion is represented analytically but a full units-of-production schedule remains backlog.
- Mine and recovery inventory uses lot-linked production cost and proportional shipment relief in implemented slices.
- Lease, income-tax, stock-compensation, impairment, and comprehensive-income logic remain simplified or unimplemented and must not be inferred from workbook tabs.
- Acquisition layers, goodwill, debt, and ARO values in the baseline are scenario inputs. Full purchase accounting schedules remain expansion work.
- Intercompany activity carries counterparty dimensions and the baseline includes a reproducible elimination example.
