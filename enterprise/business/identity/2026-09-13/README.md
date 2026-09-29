# Workforce identity bridge, September 13, 2026

This versioned bridge implements the [dated fictional appointments](../../../../docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md), pending accepted merge. Fifteen names alias existing model person/position pairs. It does not add occupied or authorized positions, salaries, paid FTE or occupied seats.

[REGISTER.json](REGISTER.json) retains exact source hashes, all original scenario workforce events, monthly alias rows and whole-roster payroll/headcount reconciliation for January 2027–December 2031. `source_model_person_id` retains the old synthetic person identifier. A position replacement or vacancy stops the prior person's alias instead of silently transferring their identity.

The generator reuses `WorkforceMixin` and the existing conditional policy, inflation, scenario cost factors, leave/return, join/exit and assignment-transfer logic. It emits no accounting entries and writes no source financial release. All 7,092 retained 2027 base-case position-month rows are compared field-for-field against the independently retained supporting schedule before the bridge is accepted. Future 2028–2031 rows are explicitly model projections, not observed employment.

Before/after whole-roster cost and authorized/occupied counts are identical because this is a label reconciliation. ESS starts at 48 occupied/54 authorized; the existing December 2027 model join can change subsequent occupancy. Internal Audit starts at 8/10, Advisory at 32/36. The named ESS, Internal Audit and Advisory slots remain inside those totals. Actual 2026 headcount/payroll, company employment start dates, physical seat assignments and concurrent attendance remain unknown.

Regenerate from repository root with `python -m enterprise.business.identity_bridge`. This creates only this version's register. Do not overwrite immutable source financial CSVs or use the bridge as an independent actual payroll census.
