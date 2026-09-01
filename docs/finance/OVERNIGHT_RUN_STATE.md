# Overnight run state

- Source: `origin/canon/corporate-lore-v0.2` at `5137c5abc025ad757a4e1af2a57279e4964578cf`
- Calibration: `origin/architecture/corporate-operating-model-v0.1` at `f12d359f3c3f009a1eea1d290f61be0462ca1f2e`
- Implementation branch: `finance/enterprise-financial-platform-v0.1`
- Current commit: `36c625c` (next accounting-control commit pending)
- Draft PR: `https://github.com/SquirmyWormy275/SABLEHARBOR/pull/9`
- Current phase: Phase 3 accounting kernel
- Completed: preflight; safe worktree; source lock; initial crosswalk; Alternative B base architecture; assumption schema; deterministic IDs; balanced journals; trial balance; posted-entry immutability; reversals; period close
- Last successful commands: `uv run ruff check .`; `uv run mypy src`; `uv run pytest` (5 passed)
- Current failures: initial cwd was not a repository; resolved by cloning the expected remote. No implementation failure open.
- Exact next command: `uv run pytest && git add src tests docs/finance/OVERNIGHT_RUN_STATE.md docs/finance/WORKLOG.md && git commit -m "feat(accounting): enforce immutable journals reversals and close"`
- Human review: legal entity chain, industrial transaction terms, consolidated quantitative baseline
- Uncommitted files: inspect with `git status --short`
