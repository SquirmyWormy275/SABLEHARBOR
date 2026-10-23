# Sable Harbor finance reconstruction

This directory contains company-specific financial archaeology and economic-model work. It is not
the Alexandria financial examination engine and does not establish financial canon.

- [Phase 0/1 financial reconstruction](SABLE_HARBOR_FINANCIAL_RECONSTRUCTION_PHASE_0_1.md)
- [Machine-readable diagnostic inputs](ECONOMIC_MODEL_INPUTS.csv)
- [Generated model outputs](model_outputs/model_summary.json)

Rebuild and validate the schedules with:

```bash
python tools/finance/build_reconstruction_model.py
python -m unittest tests.finance.test_reconstruction_model
```

Unless a row cites controlling canon and is marked `LOCKED`, values in this directory are estimates,
provisional assumptions, or scenarios. Diagnostic cases must not be copied into canon or historical
statements without an explicit decision.
