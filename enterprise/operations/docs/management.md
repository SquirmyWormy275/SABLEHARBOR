# Workforce and management development

The operating successor adds effective-dated staffing, consumption-based shared-service views and executable forecast revisions. Every population is synthetic planning evidence for 2027–2031. The accepted 2026 reconstruction and source roster remain unchanged.

## Staffing and payroll

Ten declared changes per scenario cover paid leave and return, hires into authorized vacancies, departure and replacement, an assignment transfer, and staged delivery ramps. Each month retains every authorized position in `workforce_positions_history`; occupied positions alone enter payroll. One employee's assignment fractions sum to one, salary is allocated once and paid leave supplies zero delivery hours. Ramps lower productive capacity while retaining the declared loaded salary.

Transfers change assignments within the existing position and do not create extra employment. Willow's borrowed capacity is fractional. Neither serving J2 nor the dedicated Atlas team becomes an Advisory staffing reserve. No employee name, appointment, employment date or expansion of the accepted establishment is invented by these synthetic events.

The validator reconciles position and person identities, authorization, cost, capacity and payroll journals. `workforce_changes` supplies applied change history; `workforce_assignments` supplies monthly delivery and cost allocation. Payroll entries remain requests subject to enterprise Treasury funding.

## Four shared-service pools

Technology, finance, people and assurance costs derive from actual generated ESS payroll, independent audit payroll and facility/vendor expense. The ESS split is 40%/30%/30%; audit payroll belongs to assurance and facility/vendor cost to technology. J2 mission cost and other corporate net cost stay visible as retained corporate amounts.

Each pool uses declared service commitments plus generated activity. People operations uses occupied-position payroll service demand; the other pools use platform, finance and assurance events. Industrial service assumptions remain declared planning consumption, including the separately accepted 140/131 populations. These are not observed tickets, timesheets or measured vendor utilization.

Gross allocations are offset by the existing statutory service fees for their original Pale Sun and ARU recipients. Credits are apportioned across pools exactly once. The resulting residual allocations plus retained corporate costs reconcile to corporate expense less revenue. These tables never post a second set of service charges to the legal ledger and replace the earlier illustrative FTE-only allocation in this successor. Negative residual allocations, if a recipient's existing statutory fee exceeds attributed usage, remain visible rather than being silently floored.

## Rebuilt forecasts

Three vintages are retained: the selected operating-input budget, a price-and-volume revision, and a synthetic outturn alternative with timing and staffing changes. Four cumulative model rebuilds execute the actual operating engines. Future contract pricing changes by 3%; future accepted-service fee and workload quantities change by 10%; future contract starts move one month; a further authorized Foundry Field vacancy is filled in August 2027 with a three-month ramp.

January–June 2027 is frozen and compared exactly against every rebuild. Changes apply only to later-starting populations. Revenue, net income and requested cash are derived from the rebuilt journals. The variance bridge attributes differences in the declared order: price, volume, timing, workforce. Interactions belong to the later driver; no unexplained balancing plug is created.

Budget is the selected release input set. Revised and synthetic outturn are separate management alternatives, not changes silently imported into the release ledger. “Synthetic outturn” is an exercise label, never observed actual performance. Cash is Core requested cash before enterprise Treasury, not funded group liquidity or a consolidated cash reforecast.

The register records input hashes and roles; metric histories and exact contribution rows allow independent checking. The integration calls `management.build(model, result, model_factory=OperatingModel)` only after legal and unit statements are available. `management.validate(model)` checks the source-to-view reconciliations without changing journals.
