# Turn the Taylor–Red Wash terms into a testable obligation register

**Route:** `SH-EX-CON-001`. **Question:** for each contractual requirement, what record would let a reviewer test whether it was met?

Use `SH-IND-IC-001` version `1.0.0`, the reconstructed Taylor–Red Wash logistics agreement summary effective **July 7, 2026**, with term through **July 6, 2031**. Review obligations as documented at the source's September 5, 2026 publication cutoff. This is a source-term extraction exercise, with no financial scenario selected and no claim that future services have occurred. Native parties are `ARU`, `BST` and `RWH`.

## Open the complete existing source

Read the [full agreement summary](../../../industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md) or its [existing complete PDF](../../../industrial/publications/SH-IND-IC-001_v1.0.0.pdf). Read “Parties, authority and term” and **all four schedules A–D**. The short [reader record](../../legal/evidence/commercial/SH-LEGAL-READ-IC-001.md) helps navigation but is not a replacement for the complete source. Its [source/section database](../transactions/legal-records.sqlite3) is optional.

This existing source is explicitly a synthetic reconstructed agreement summary, not an authentic executed agreement. Reproducing its full text does not supply signatures, insurer certificates or an external carrier tariff.

## Work through it

1. Create a working register with columns: source ID and heading, obligated party, recipient, required action, trigger, timing, evidence needed, evidence supplied, and conclusion. Use one row for each requirement you choose to test. Distinguish an obligation from a right, planning assumption or operating goal.
2. From “Parties, authority and term,” separate BS&T rail service from ARU terminal/trucking service and RWH receiving duties. Record the billing-agent distinction. Ownership by a parent does not make that parent the performing carrier.
3. From **Schedule A**, select one ordinary commodity and transcribe its rail, terminal, truck-trip and combined rate basis. Specify the quantity and accepted rate-version evidence needed to reperform an invoice. Record why the 225-slot allowance, 300-slot design capacity and lack of a minimum-volume guarantee cannot establish billed service. Do not invent a shipment or invoice to fill the register.
4. From **Schedule B**, extract the interchange-to-empty-release limit, steel exception, operating goal and customer-caused storage rule into separate rows. Identify start/end timestamps, timezone, cause and charging entity as needed evidence. Explain how elapsed-time testing differs from simply counting scheduled handling windows. Where supporting events are not supplied in the reading packet, conclude “not tested—event evidence required,” not “compliant.”
5. From **Schedule C**, list the custody events and qualification/insurance evidence required for ordinary inbound service. Keep stated synthetic coverage assumptions separate from actual policy evidence. Record `OPEN_GATED` uranium-product custody as an excluded, separately gated service; do not treat ordinary acid qualification as authorization for uranium.
6. From **Schedule D**, extract actual-quantity monthly billing, 30-calendar-day payment terms, asset ownership, breach cure and convenience termination. Record triggering notice/evidence for a deadline; do not fabricate a notice date or claim that a future deadline has passed. Explain why the model's following-month settlement convention alone cannot prove payment within 30 days of a particular invoice.
7. Add a missing-evidence column for genuine performance testing: shipment/custody timestamps, rate amendment where applicable, invoice, payment evidence, qualification records, policy evidence, cause allocation and notice correspondence. Mark which are absent from this reading packet. “Absent here” does not mean absent everywhere in the repository or proof of breach.

## Hand in and review

Deliver a clause-based obligation register and a prioritized evidence-request list. Each row must point to the exact source heading, identify the performing party and state what would support a conclusion. Have a colleague distinguish your contractual deadlines from goals and capacity assumptions without consulting you.

No new contract terms, execution status or service-performance findings are created. Third-party linehaul and carrier charges require their own governing terms and supporting invoices. The source excludes a Red Wash mine spur and direct uranium custody; the exercise must preserve both boundaries. The result is a reading and evidence-design exercise, not an assertion of legal compliance or an executed amendment.

[Return to the three exercises](README.md)
