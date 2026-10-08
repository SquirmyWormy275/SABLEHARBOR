# Reviewed fictional 2027 source portfolio diagnostic

`fictional_2027_source_portfolio.py` is a read-only gate over ten independently reviewed company-native training-world source cohorts. It reruns each source's own verifier in dependency order and checks its independent review digest, private file modes, sidecar absence, exact manifest/receipt/database hashes, immutable file identities, SQLite integrity, empty audit access journals, native version count and explicit no-credit result. It reports the physical source company ID so `SABLE-HARBOR-REFERENCE` remains distinct from the frozen audit profile's `SABLEHARBOR`.

Run from a checkout with the private reviewed sources present:

```bash
python -m enterprise.audit_suite.fictional_2027_source_portfolio \
  --repository /home/kingoftheeast/Projects/SABLEHARBOR-audit-suite
```

At the September 29 checkpoint the diagnostic finds ten cohorts and 178 native versions across their Clean/Messy branches. It creates no registry, grant, collection, audit task change, Key, grade or new source history. The active 13-component pair remains frozen; its 409 tasks per branch are still unstarted/unrun. The reviewed [source-route tracker](../../docs/internal/development/audit-suite/2027_SOURCE_ROUTE_TRACKER_2026-09-29.md) and [50-route data ledger](DATA_RECORD_PHI_50_ROUTE_GAP_LEDGER_2026-09-29.md) give the remaining design/procedure limits. A fresh zero-evidence pair is required after a separately reviewed source-complete registry.

This gate is deliberately fixed to a partial roster. New cohorts require explicit code and review-digest updates followed by an independent recheck. A passing report is source integrity at the selected checkpoint, not a 2027 operating-year assertion, evidence sufficiency or SOC 2/HIPAA conclusion.
