# Company edition dependency remediation — September 22, 2026

Company source acceptance: PR #166, merge `357888ef3c936892fa2451f68613f3019e5811a8`.
This maintenance successor changes the supported dependency environment and its audit workflow; company decisions and immutable historical publications retain their scope. Acceptance follows the actual merge of this maintenance PR. The final company release receipt identifies that merge and validation on its exact revision.

## Findings and correction

The pre-publication installed-environment scan found 25 known advisories across three packages. Publication was withheld for correction. The isolated patched environment reports zero known advisories across 45 third-party distributions. These results describe the advisory database consulted on September 22, 2026; they are not a guarantee against unknown vulnerabilities.

| Package | Previous | Patched | Earlier findings |
|---|---|---|---:|
| PyMuPDF | 1.26.6 | 1.26.7 | 1 |
| pypdf | 6.10.0 | 6.16.1 | 23 |
| pytest | 8.4.2 | 9.0.3 | 1 |

`pyproject.toml`, `uv.lock` and six standalone requirements files carry the applicable updates: documents, legal gaps, reader, organization, geospatial, and legal full-text tools. All ten supported standalone requirements populations were audited with zero known findings, including four additional wiki, visual, review and preview routes that did not require pin changes. Only the three package lock records changed. No source-lock exception, advisory suppression or frozen publication replacement was used. The local editable `sable-harbor-finance` package is explicitly skipped by the external advisory service because it is not a PyPI distribution; repository tests cover its implementation.

Primary advisory records were checked for withdrawal and affected/patched ranges: [PyMuPDF](https://github.com/advisories/GHSA-cxqh-p2w9-fmr7), [pypdf latest required patch](https://github.com/advisories/GHSA-763m-79hh-57f2), and [pytest](https://github.com/advisories/GHSA-6w46-j5rx-g56g). The full before scan retains all 25 advisory identifiers.

## Reproduction and retained evidence

Run `uv sync --frozen --all-extras`, then audit the installed environment:

```bash
audit_site="$(uv run python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')"
uvx --from pip-audit==2.9.0 pip-audit --path "$audit_site" --skip-editable --progress-spinner off --format json --output dependency-audit.json
```

[Before scan](evidence/dependency-remediation-2026-09-22/before-audit.json), [patched scan](evidence/dependency-remediation-2026-09-22/after-audit.json), primary advisory API responses and [18 pinned canon blob checks](evidence/dependency-remediation-2026-09-22/source-lock-verification.json) preserve the failure and correction. The patched focused publication suite passed 24 tests; all 30 approved publication artifacts remained protected. The complete patched suite passed 749 tests with five skips: three require an external PostgreSQL test URL and two require optional Pillow. The two PDF image tests passed separately with ephemeral Pillow 12.3.0, yielding 751 exercised passes and three external PostgreSQL skips across the runs. The release's validation receipt supplies complete-suite results, commands, source revision and final environment scan, rather than treating this preliminary scan as final release validation.

The legal-publication validator initially rejected its historical build-input requirements hash after the version updates. [The exact toolchain successor](../../legal/gap-instruments/dependency-successors/PR168-toolchain.json) preserves the original requirements bytes and verifies only the two approved version replacements, without changing the historical manifest or any publication hash. It applies only to build-input records; source and artifact slots remain strict. The actual legal validator and its previously failing package test passed after correction; mutation tests reject changed or missing provenance. The original hosted failures remain available in PR #168, and the final release retains their logs.

The pinned dependency-audit workflow runs on changes to the project or standalone installation paths, the lock or its own configuration, and can also be dispatched. It retains failed as well as successful audit JSON. It does not access the active portal's environment or data. Final release generation uses the patched supported environment and a new generation identity; preserved releases keep their original source bytes.
