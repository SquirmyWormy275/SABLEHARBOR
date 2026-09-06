# Industrial acquisition and operating case guide

**Document ID:** SH-IND-CASE-001 | **Version:** 1.0.0
**Owner:** Sable Harbor Industrial Holdings
**Effective date:** 2026-09-05 | **Available at:** 2026-09-05T23:59:59-07:00
**State:** SELECTED_SYNTHETIC_CASE
**Record origin:** PUBLIC_SYNTHETIC_DIEGETIC

This corpus follows the creation of Pale Sun, its acquisition and stabilization of Red Wash, and the acquisition of ARU with its BS&T railroad subsidiary. The company has a reason to own each business independently. The mine remains dependent on qualified external carriers for uranium movements. ARU begins a limited ordinary-inbound interface on July 7, 2026; a mine spur and direct uranium custody remain unapproved options.

## Read the company before the spreadsheets

1. [Legal structure and formation](corporate/LEGAL_STRUCTURE_AND_FORMATION.md) establishes the ownership chain. [Leadership and authority](corporate/LEADERSHIP_AND_AUTHORITY.md) separates executive, operating, safety and advisory roles.
2. The ten records under `industrial/pale_sun/` begin with [Evan Vilander's biography](pale_sun/01_VILANDER_BIOGRAPHY.md), follow BTC recruitment and J2 work through three unsuccessful uranium opportunities, and end with the Red Wash after-action review and federal/downstream brief.
3. The records under `industrial/transaction/` distinguish the [Red Wash transaction](transaction/01_RW_TRANSACTION_FILE.md), ARU seller engagement, diligence, purchase approval, closing/tax delivery, transition and tax structure. The service agreement and pricing comparison define the intercompany operating terms. These are clearly marked synthetic company records, not government-issued certificates or proof of real execution.
4. The operating records under `industrial/operations/` explain the railroad, facilities, labor, safety, shipment calendar, service prices and capital program. The financial records under `industrial/finance/` explain how those activities reach the books and cash requirements.
5. The mine documents under `red_wash/` provide geology, mine planning, processing, regulatory obligations, commercial instruments and transport dependencies. The current site and underground maps are in `industrial/visuals/`.

## Follow an amount or a movement

The structured inputs are `industrial/source/entities.json`, `chronology.json`, `operations.json`, `finance.json`, and the selected mine inputs under `red_wash/source/`. Generated operating registers describe physical assets, people, labor agreements and capital projects. Generated finance schedules carry contracts through monthly revenue, payroll and other costs into balanced journals, trial balances, cash flow, debt, fixed assets and intercompany eliminations.

The archive's `industrial_case.sqlite3` combines selected CSV tables without merging their distinct scopes. `artifact_lineage` identifies each table's source file, checksum, availability, effective date, fact state and temporal mode. Table prefixes identify `finance`, `operations` and the separate `red_wash` standalone scope. Currency columns ending `_usd` are whole US dollars unless a source explicitly specifies a rate. Physical units remain explicit; uranium pounds, ore short tons, route miles, track miles and railcar movements are different measures.

## Dates and evidence

The retrospective cutoff is September 5, 2026, at 23:59:59 Pacific daylight time. Event date, fictional company availability, real editorial creation and publication cutoff answer different questions. The manifest records the basis for selecting each artifact. A reconstructed 2024 memo can describe a 2024 fictional decision without claiming that its present digital file existed then. Historical dates with year or month precision remain intervals in the chronology.

No record with unknown company availability is eligible. An artifact containing a future effective date must be identified as a forecast, commitment or option known at the cutoff. Full September financial periods fall after the cutoff; they remain forecasts. The January–August model layers are synthetic calibrations, not observed actuals. Scheduled January 2027 retention payments, future mine expansions and closure cash flows remain commitments or estimates rather than realized facts.

## Deliberate business limitations

The freight plan provides 205 recurring cars, ten project cars and ten conditional buffer slots in a 225-car planning envelope. The normalized base invoices cover 215 used cars. Capacity to handle 300 cars is a design allowance, not a sales forecast. The 2026 start-up ramp is separately scheduled and billed.

The $8.5 million interface program belongs to two owners: $3.25 million at Red Wash and $5.25 million at ARU. The remaining $6.5 million of the old $15 million screening ceiling is unapproved capacity in the screen, not another asset or funding source. ARU's $11 million catch-up program and annual sustaining capital are separate.

The mine's standalone financial comparison and integrated successor are separate scopes. The successor carries its own ARO rollforward, interface costs, depreciation, taxes and equity support. ARU's intercompany revenue and Red Wash's matching expense eliminate at the industrial operating consolidation. External costs and cash consumption remain. Derived service economics are allowed to miss an earlier target; no balancing revenue or cost-saving plug is used.

The source geography distinguishes real public reference features from fictional railway alignments, facilities and access rights. A map or synthetic inspection record does not establish a surveyed right-of-way, engineering sign-off or government approval. The mine's unresolved diligence issues and the railroad's maintenance and safety obligations remain visible.
