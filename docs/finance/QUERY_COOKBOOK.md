# Query cookbook

List queries with `shfin queries` and execute one with
`shfin query NAME --generation-run-id RUN_ID`. SQL sources are versioned in `db/sql/`, use the
selected compatible run context, and execute against SQLite and PostgreSQL-compatible tables without
interpolating user input.

`scenario_variance` is deliberately a two-run query. Execute it with
`shfin query scenario_variance --generation-run-id SELECTED_RUN_ID
--comparison-generation-run-id COMPARISON_RUN_ID`. Both runs must be distinct completed scenarios
with the same profile, seed, source/input build, schema, cutoff, and shared synthetic calibration
dataset. Shared pre-cutoff values therefore compare at zero; only scenario-owned values can vary.

Implemented names cover consolidated monthly P&L, entity trial balance, bidirectional journal/source
tracing, ARR and customer profitability, engagement/WIP interface, employee loaded cost, vendor
concentration, AR/AP exposure reconciliation, deferred revenue, fixed assets, mine inventory and unit
cost, BS&T route/customer margin, Cradle economics, intercompany, debt covenant availability, scenario variance,
assumption impact, and release coverage/lineage. The exposure query is
`ar_ap_exposure_reconciliation`: it ages AR where due dates exist, labels AP due dates unavailable,
and discloses the residual source-event bridge required to reconcile document balances to the GL.

The standard synthetic profile populates the engagement subledger, so the engagement query returns
causal revenue, cost, and WIP evidence for that profile. Profiles that omit the engagement subledger
can legitimately return no rows. In every case, the query is an executable interface over generated
synthetic evidence, not a claim that observed engagement records exist.
