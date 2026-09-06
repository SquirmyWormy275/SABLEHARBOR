# Procurement, transaction evidence and cash reconciliation

**Document ID:** SH-PLAN-EVIDENCE-002
**Version:** 2.0.0
**Owner:** Industrial finance and treasury
**Available at:** 2026-09-06T00:00:00-07:00
**State:** Prospective synthetic planning evidence

The successor distinguishes inputs that determine the accounts from documents reconstructed from those accounts. Neither is independent external corroboration. The controlled input is `industrial/planning/source/transaction_policy.json`; the implementation is `industrial/planning/transactions.py`.

## Procurement determines purchased-service expense

The initial nonpayroll cost envelope is the inherited 2025 segment expense less census-derived payroll and the explicit corporate allocation. Twenty-five category/segment combinations cover purchased materials and fuel, equipment maintenance, occupancy and utilities, insurance/environmental services, and other external operating services. The derived starting unit rates are labeled calibrated synthetic rates, not supplier quotations.

Variable purchased quantities follow each scenario's own physical activity. Outsourced customer fulfillment does not also consume owned-operation variable procurement. Fixed service commitments continue during reduced utilization. The cost index changes prices explicitly. Incremental disruption repairs, outside carriers, payroll and capital are separately recognized once in the financial model. A future margin is not used to solve for an expense rate.

Each purchase has a stable item identifier, fictional supplier, order, receipt/service acceptance and invoice. Maintenance purchases additionally have a work order. The model verifies quantities, amounts, counterparties, scenario membership and chronology across the three-way match. Invoice identifiers reach the expense and payable posting and the cash-settlement record. Payment delay or a funding shortfall cannot silently erase an unpaid invoice.

A materials receipt can represent consumption through an existing replenishment arrangement; it is not an independently surveyed warehouse count. Physical mine acid/binder/product balances and the operating scenario's inventory controls retain their separate units and owner. The transaction record does not merge ore tons, uranium pounds, freight units and service units.

## Other evidence reconstructs declared forecast events

Sales invoices, payroll batches and the event register reconstruct the ledger's declared forecast recognition and settlement. They identify their source contracts, physical drivers or other planning assumptions. This creates a document-to-journal path without claiming that a generated document independently proves the premise that generated it.

Monthly service manifests allocate realized segment volume among invoiced contracts by their accepted annual physical-unit weights. Railcars and dispatches remain integral; other handling units use three decimal places. These are transparent planning allocations, not observed individual waybills. Their segment totals reconcile to realized operations and their revenue links to the sales journal. Customer-level revenue also includes contract reservations and accessorials, so allocated units are not a replacement tariff calculation.

Payroll role details allocate each employer-cost batch and its eventual settlement using the accepted census compensation weights. Accepted census role capacities remain fixed in expansion. Additional drivers, terminal handlers and warehouse workers occupy separate planned position pools matching the operating plan. Their employer-cost weights use the forecast segment-average budget proxy; management roles are not proportionately multiplied. The records are role allocations, not individual payslips or payroll tax filings. Unpaid batch amounts remain explicit.

Banking evidence uses the source ledger's treasury scope. A consolidated ARU or mine cash scope is identified as such; it is not relabeled an independently reconstructed statutory bank account. Separate legal-entity cash statements are supplied by the enterprise integration. No real account numbers, payment endpoints, private contact details or executed signatures are invented.

Monthly ledger cash events use a month-end posting convention; procurement documents separately retain their modeled invoice and due dates. The bank clearing schedule applies a disclosed two-day interval after modeled posting. At a month boundary this creates deposits in transit and outstanding payments. Opening bank cash plus cleared receipts less cleared payments equals closing bank cash. Closing bank cash plus deposits in transit less outstanding payments equals book cash. Both identities are tested independently of the forecast statement totals.

Every record remains prospective and synthetic. The original September 5 participant snapshot remains unchanged. The successor package includes the source policies and exact file hashes, and its browser follows identifiers across procurement, journal, sales and payment records.
