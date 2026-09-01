# Query cookbook

List queries with `shfin queries` and execute one with `shfin query NAME`. SQL sources are versioned in `db/sql/` and execute against SQLite and PostgreSQL-compatible tables without interpolating user input.

Implemented names cover consolidated monthly P&L, entity trial balance, bidirectional journal/source tracing, ARR and customer profitability, engagement/WIP interface, employee loaded cost, vendor concentration, AR/AP aging, deferred revenue, fixed assets, mine inventory and unit cost, ARU margin, Cradle economics, intercompany, debt covenant availability, scenario variance, assumption impact, and release coverage/lineage.

The engagement query intentionally returns no rows until the detailed engagement subledger is populated; it is an executable interface, not a claim that engagement data already exists.
