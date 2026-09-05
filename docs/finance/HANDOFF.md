# Handoff

Work from the repository root. Read `CANON_SOURCE_LOCK.json` and `OVERNIGHT_RUN_STATE.md` first.
Current v0.3 canon plus the September 3 addendum controls from its
effective dates; v0.2 is only the August 31 historical knowledge snapshot. The working model is not
canon: all generated 2023–2026 numbers are synthetic scenario/calibration records and new
quantitative structure remains `MODEL_PROPOSED` or `SCENARIO_INPUT`.

If GitHub authentication blocks automation, push with:

```bash
git push -u origin finance/enterprise-financial-platform-v0.1
gh pr create --draft --base main --head finance/enterprise-financial-platform-v0.1 --title "Build Sable Harbor enterprise financial data platform v0.1"
```
