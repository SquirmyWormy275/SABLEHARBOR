# Repository checks

From a clean checkout, run `make bootstrap`, then `make ci`. Bootstrap uses the committed
lockfile and includes the PDF and Markdown libraries imported by repository tests.
The root pytest configuration adds the repository root to Python’s import path, so both `uv run pytest` (used by `make ci`) and `uv run python -m pytest` collect the tools-based tests correctly. It does not install browsers. The finance guide's database steps remain optional for
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

## Choose a check for your change

Run `make help` for the command list. These targets use the same committed dependencies
and validators as CI; focused checks do not replace a full applicable CI run.

| Change | Local command | Scope |
|---|---|---|
| Small code or Wiki edit | `make check-fast` | Root lint/types plus Wiki navigation, accessibility, exporter and publication-guard tests |
| Wiki links or prose | `make check-wiki` | All Wiki pages, local anchors, Home reachability, heading order and image/link descriptions |
| Wiki layout | `make wiki-visual` | Real Chromium rendering with screenshots; install the separately pinned browser first as shown above |
| Geographic adjudication | `make check-geo-review` | Reproduce all reviewed batches and test their source bindings |
| Business operations | `make check-operations` | Operations/business/planning tests without building full distribution packages |
| Root code before delivery | `make ci` | Full root suite, lint and types |

Business-operations CI now performs both complete distribution builds in separate clean
runners. A reconciliation job waits for the original test suite and both builds, verifies
both checksum manifests, compares every distribution file byte for byte, and only then
uploads the accepted artifact consumed by the existing publication job. No build is reused
from a prior commit and no reproducibility check is skipped. The two builds consume more
concurrent runner capacity but remove the serial second-build wait.

## Publish the accepted Wiki

The live Wiki is initialized. From a clean checkout of current accepted main, run
`make wiki-publish` using existing local Git authentication. The command fetches the public
main reference, refuses dirty or unaccepted source, exports into temporary directories,
preserves unmanaged Wiki pages/history, pushes without force and verifies a fresh remote
clone against every exported page hash. `var/wiki-publication.json` records the result.
No credential is copied into repository secrets. The manual Actions workflow remains an
alternative when its `WIKI_TOKEN` is configured. See [publication status](../../docs/wiki/README.md).
