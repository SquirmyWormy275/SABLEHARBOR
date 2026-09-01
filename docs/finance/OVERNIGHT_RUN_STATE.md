# Overnight run state

- Source: `origin/canon/corporate-lore-v0.2` at `5137c5abc025ad757a4e1af2a57279e4964578cf`
- Calibration: `origin/architecture/corporate-operating-model-v0.1` at `f12d359f3c3f009a1eea1d290f61be0462ca1f2e`
- Implementation branch: `finance/enterprise-financial-platform-v0.1`
- Current completed baseline commit: `72b2754`
- Draft PR: `https://github.com/SquirmyWormy275/SABLEHARBOR/pull/9`
- Current phase: Phase 6 handoff and expansion backlog
- Completed: source lock; collision registers; alternatives A/B/C; selected Alternative B; corporate operating model; legal/entity scenario; dimensional chart of accounts; immutable accounting kernel; migrations; contract-to-cash; payroll, procurement, asset and debt flows; industrial operational tables; deterministic 708-employee baseline; consolidation eliminations; reconciled reporting workbook proof
- Last successful command: `uv run ruff check . && uv run mypy src && uv run pytest` (11 passed); full generation validation balanced at debit = credit = `$750,600,000.0000`; workbook ZIP validation passed
- Current failures: initial cwd was not a repository; resolved by cloning the expected remote. No implementation failure open.
- Exact resume command: `cd /home/kingoftheeast/Projects/SABLEHARBOR-finance && uv run shfin generate --profile full --scenario base --seed 20260831 && uv run shfin validate && uv run shfin report && make ci`
- Human review: legal entity chain, acquisition/PPA and financing terms, mine/ARU driver ranges, board and named executive structure
- Uncommitted files: inspect with `git status --short`
