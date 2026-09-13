# Contributing to Sable Harbor

[Repository home](README.md) · [Maintainer rules](MAINTAINERS.md) · [Source and status guide](docs/reader/SOURCES_AND_FORMATS.md) · [Open questions](docs/wiki/Open-Questions.md)

Sable Harbor is a fictional enterprise archive with executable models and a published reading edition. A useful contribution makes an existing record clearer, repairs a supported implementation or delivers an explicitly authorized decision with its evidence. Presentation work must preserve what remains provisional or unknown.

## Start with a defined change

Read the relevant source and its status before editing. Identify the affected businesses, controlling records, generated outputs and release boundaries. Check open pull requests and worktree ownership so concurrent work stays separate.

Use an isolated branch from refreshed main:

```bash
git fetch origin main
git worktree add -b work/my-change ../SABLEHARBOR-my-change origin/main
cd ../SABLEHARBOR-my-change
```

Do not retire another contributor's branch or overwrite their generated output. Reconcile shared catalogs against the latest main during integration.

## Set up development

The root project requires Python 3.11 or later, `uv` and `make`. The frozen dependency lock is the reproducible starting point:

```bash
make bootstrap
make check-fast
```

`make help` lists the available checks. Package READMEs describe additional tools needed for their own builds. Reading Markdown, PDFs and downloaded workbooks does not require this setup.

## Choose checks that match the change

| Change | Validation route |
|---|---|
| Ordinary source or implementation change | `make check-fast`, then the relevant package or domain tests. |
| Wiki content or navigation | `make check-wiki`, a complete export and the composed-page browser review below. |
| Canon, governance, organization or catalogs | The required validators and full suite listed in [MAINTAINERS.md](MAINTAINERS.md). |
| Geographic adjudication | `make check-geo-review` and the affected geographic package's documented checks. |
| Business or operating models | `make check-operations` and the affected model's reconciliation and packaging checks. |

Use the [CI guide](tools/ci/README.md) for required environments, test partitions and retained evidence. Do not interpret a passing software test as evidence that a real control, transaction or operating process occurred.

## Review a Wiki change

Curated articles live under `docs/wiki/`. Full records are selected by `tools/wiki/reading.json`; readable publication titles are inventoried in `tools/wiki/titles.json`. Preserve existing addresses when changing published titles. Edit sources and selections rather than the live Wiki.

```bash
wiki_review_dir=$(mktemp -d)
uv run python tools/wiki/export.py --revision "$(git rev-parse HEAD)" --output "$wiki_review_dir"
uv run python -m tools.wiki.audit --export "$wiki_review_dir"
uv run --with-requirements tools/wiki/visual/requirements.txt playwright install --with-deps --only-shell chromium
uv run --with-requirements tools/wiki/visual/requirements.txt python -m tools.wiki.visual.export --export "$wiki_review_dir"
```

The review checks every canonical page in light and dark themes at mobile and desktop widths. Historical address routes and section links are checked in the complete export. Inspect representative screenshots as well as the machine-readable result.

## Preserve sources and generated records

Keep one controlling source for each decision. Stage new Markdown before regenerating the shared catalog: its inventory uses Git-tracked files. Regenerate generated records with their documented tools, and review the resulting diff against current main.

Approved artwork retains its exact bytes and authority. A chart, catalog entry or repeated generated record does not create a new appointment, ownership relationship or fact. Source-locked releases retain their original snapshots.

Follow [MAINTAINERS.md](MAINTAINERS.md) for controlled publications and [the delivery policy](docs/governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md) for packages, manifests and acceptance evidence. Explicit task ownership and current user instructions govern concurrent publication work.

## Submit and deliver

Open a pull request that explains the concrete problem, resulting behavior, controlling sources, validation and remaining limits. Keep unrelated formatting and renaming out of the change. Merge only after the relevant checks pass for the reviewed head and any current-main integration is resolved.

After acceptance, a Wiki change can be published from a clean refreshed main checkout with `make wiki-publish`. Run `make wiki-freshness` to verify the result against the remote pages and current reading inputs. Publish packages through their indexed release workflow rather than treating scratch outputs as delivery.

Close an issue only when its remaining acceptance criteria are supported by accepted evidence. Missing decisions and execution records stay open. Report sensitive findings through the route in [SECURITY.md](SECURITY.md); the [license](LICENSE.md) defines reuse rights.
