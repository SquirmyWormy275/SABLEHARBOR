# Repository checks

From a clean checkout, run `make bootstrap`, then `make ci`. Bootstrap uses the committed
lockfile and includes the PDF and Markdown libraries imported by repository tests.
It does not install browsers. The finance guide's database steps remain optional for
SQLite tests; PostgreSQL integration tests require their documented test database.

Finance CI runs the complete collected root test suite in three isolated checkouts.
`shard.py` assigns every collected node ID exactly once using descending recorded duration
and the least-loaded shard. Unknown tests receive a one-second estimate and are included
automatically. Each shard retains pytest's collection order and runs serially: some document
tests regenerate repository files, so shared-checkout parallel execution is inappropriate.
SQLite delivery, PostgreSQL delivery, lint, types and evidence checks retain their gates.

The September 12 clean-environment baseline was 183 passed, three environment-dependent
skips in 219.70 seconds on the local machine. `test_weights.json` contains those observed
per-test seconds, used only for scheduling, never selection or pass/fail. CI uploads JUnit
results and prints its slowest tests so future balancing can use measured results.
Local timing is not a promise about hosted-runner performance.

To reproduce one shard (indices 0–2):

```bash
SHFIN_TEST_SHARDS=3 SHFIN_TEST_SHARD=0 uv run python -m pytest -p tools.ci.shard
```

Workflow jobs have distinct human-readable names without changing their internal IDs or
release triggers. The governance/J2 workflow remains owned by the legal-publication session;
its existing `validate` check is the sole retained generic name.

## Wiki browser review

```bash
uv run --with-requirements tools/wiki/visual/requirements.txt playwright install --with-deps --only-shell chromium
uv run --with-requirements tools/wiki/visual/requirements.txt python tools/wiki/visual/check.py
```

The separate Wiki visual workflow reviews every business and department detail page and
Wiki Home at 390px and 1280px in light and dark themes. It checks images, header opacity
and visual variation, approved header hashes, page overflow and scrollable wide tables.
Screenshots and JSON results are saved in `var/wiki-visual` and uploaded by CI. This uses
an approximation of GitHub styling through the existing local preview, not the live Wiki
or a pixel-perfect assertion about GitHub's renderer. Browser dependencies are separately
pinned. Header hash changes require explicit review; never regenerate the inventory merely
to make a changed or missing asset pass. The publication workflow remains manual.
