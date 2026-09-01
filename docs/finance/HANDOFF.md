# Handoff

Work in `/home/kingoftheeast/Projects/SABLEHARBOR-finance`. Read `CANON_SOURCE_LOCK.json` and `OVERNIGHT_RUN_STATE.md` first. The working model is not canon: all new quantitative structure remains `MODEL_PROPOSED`.

If GitHub authentication blocks automation, push with:

```bash
git push -u origin finance/enterprise-financial-platform-v0.1
gh pr create --draft --base canon/corporate-lore-v0.2 --head finance/enterprise-financial-platform-v0.1 --title "Build Sable Harbor enterprise financial data platform v0.1"
```
