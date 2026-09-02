# Blackridge Validation and Reconciliation

Validation checks SQLite integrity, foreign keys, journal balance, derived impairment range, and
public-oracle leakage. Automated corruption testing proves an altered journal is rejected, and
snapshot testing proves future-available events are excluded. Reports are machine-readable JSON;
green results do not promote independent acceptance automatically.

