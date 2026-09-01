# Overnight run state

- Source: `origin/canon/corporate-lore-v0.2` at `5137c5abc025ad757a4e1af2a57279e4964578cf`
- Calibration: `origin/architecture/corporate-operating-model-v0.1` at `f12d359f3c3f009a1eea1d290f61be0462ca1f2e`
- Implementation branch: `finance/enterprise-financial-platform-v0.1`
- Current completed platform branch: `finance/enterprise-financial-platform-v0.1` (final verification commits follow `281deac`)
- Draft PR: `https://github.com/SquirmyWormy275/SABLEHARBOR/pull/9`
- Current phase: Platform v0.1 complete; release verification and canon review
- Completed: source lock and collisions; alternatives A/B/C; Alternative B operating model; legal/entity scenario; dimensional chart; immutable accounting kernel; migrations; commercial and corporate subledgers; Red Wash, ARU/BS&T, Cradle, Willow and Atlas causal flows; deterministic base/low/high/stress profiles; 2023–2026 monthly standard model; 2016–2026 history; intercompany eliminations; reconciled statements; named queries; six-workbook suite; valuation; public release package; privacy/canon guardrails; SQLite and PostgreSQL CI definitions
- Last successful local release: clean migration; `full_history` generation; trial balance debit = credit = `$1,172,100,000.0000`; six workbooks; public package; valuation; statement balance difference `$0.0000`; lint/type checks; 27 tests passed
- Current failures: initial cwd was not a repository; resolved by cloning the expected remote. No implementation failure open.
- Exact resume command: `cd /home/kingoftheeast/Projects/SABLEHARBOR-finance && SHFIN_DATABASE_URL=sqlite:///var/release.db uv run alembic upgrade head && SHFIN_DATABASE_URL=sqlite:///var/release.db uv run shfin generate --profile full_history --scenario base --seed 20260831 && SHFIN_DATABASE_URL=sqlite:///var/release.db uv run shfin validate && SHFIN_DATABASE_URL=sqlite:///var/release.db uv run shfin workbooks && SHFIN_DATABASE_URL=sqlite:///var/release.db uv run shfin package-release && make ci`
- Human/canon review: legal entity chain, acquisition/PPA and financing terms, mine/ARU driver ranges, board and named executive structure. These remain deliberately reversible and do not block platform operation.
- Uncommitted files: inspect with `git status --short`
