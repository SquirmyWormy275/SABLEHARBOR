# Contributing to Sable Harbor

[Repository home](README.md) · [Maintainer rules](MAINTAINERS.md) · [Source and status guide](docs/reader/SOURCES_AND_FORMATS.md) · [Open questions](docs/wiki/Open-Questions.md)

Sable Harbor's repository holds the company records and models; the Wiki helps people read and use them. A useful contribution makes a record clearer, fixes an implementation, or puts an approved decision into practice with supporting evidence. Editing the presentation must not turn an unanswered question into a settled fact.

## Write for people

Write as a knowledgeable colleague explaining the company to another person. Start with the subject: what the business does, who is responsible, what happened, or what the reader can do next. Explain the repository machinery only where someone needs it to complete a task.

- Use ordinary words and concrete verbs. Prefer "supporting records" to "evidence surfaces," "reader's guide" to "reading layer," and "the records covered by this exercise" to "bounded evidence population." Keep technical terms when they carry a precise meaning, and explain unfamiliar ones on first use.
- Keep qualifications specific and close to the claim they qualify. Explain what is missing and why it matters. Do not repeat the same general warning in every section or replace it with vague reassurance.
- Make links useful: say what readers will find or do there. Preserve existing addresses and section anchors when editing titles.
- Preserve substance. Do not change names, figures, dates, ownership, reporting lines, decision states, quoted source wording, code identifiers, or immutable release files as part of a prose cleanup. Edit generated wording in its source or generator, not in the output.

Before submitting, read the changed passages aloud. Remove sentences that merely announce the document's seriousness, repeat its status, or describe the act of documenting instead of the subject. Keep the detail someone needs to understand the work or check a conclusion.

## Start with a defined change

Read the relevant source and its status before editing. Identify which businesses, authoritative records, generated files, and releases the change affects. Check open pull requests and who is working in each worktree so you do not overwrite work in progress.

Use an isolated branch from refreshed main:

```bash
git fetch origin main
git worktree add -b work/my-change ../SABLEHARBOR-my-change origin/main
cd ../SABLEHARBOR-my-change
```

Do not retire another contributor's branch or overwrite their generated output. Reconcile shared catalogs against the latest main during integration.

## Set up development

The root project requires Python 3.11 or later, `uv` and `make`. Start with the locked dependency versions:

```bash
make bootstrap
make check-fast
```

`make help` lists the available checks. Package READMEs describe additional tools needed for their own builds. Reading Markdown, PDFs, and downloaded workbooks does not require this setup.

## Choose checks that match the change

| Change | Validation route |
|---|---|
| Ordinary source or implementation change | `make check-fast`, then the relevant package or domain tests. |
| Wiki content or navigation | `make check-wiki`, a complete export and the composed-page browser review below. |
| Canon, governance, organization or catalogs | The required validators and full suite listed in [MAINTAINERS.md](MAINTAINERS.md). |
| Geographic adjudication | `make check-geo-review` and the affected geographic package's documented checks. |
| Business or operating models | `make check-operations` and the affected model's reconciliation and packaging checks. |

The [CI guide](tools/ci/README.md) explains the required environments, test groups, and saved results. Passing a software test does not prove that a control was performed, a transaction occurred, or an operating process worked.

## Review a Wiki change

Edit articles under `docs/wiki/`. `tools/wiki/reading.json` selects the full records included in the Wiki, and `tools/wiki/titles.json` defines their published titles. Preserve existing addresses when changing titles. Edit these sources and selections rather than the live Wiki.

```bash
wiki_review_dir=$(mktemp -d)
uv run python tools/wiki/export.py --revision "$(git rev-parse HEAD)" --output "$wiki_review_dir"
uv run python -m tools.wiki.audit --export "$wiki_review_dir"
uv run --with-requirements tools/wiki/visual/requirements.txt playwright install --with-deps --only-shell chromium
uv run --with-requirements tools/wiki/visual/requirements.txt python -m tools.wiki.visual.export --export "$wiki_review_dir"
```

The review checks every canonical page in light and dark themes at mobile and desktop widths. It also checks older page addresses and section links in the complete export. Inspect representative screenshots as well as the automated results.

## Preserve sources and generated records

Keep one authoritative source for each decision. Stage new Markdown before regenerating the shared catalog: its inventory uses Git-tracked files. Use the documented build tools to regenerate files, then review the diff against current main.

Preserve approved artwork exactly. A chart or catalog entry does not create a new appointment, ownership relationship, or fact. Source-locked releases keep their original snapshots.

Follow [MAINTAINERS.md](MAINTAINERS.md) for controlled publications and [the delivery policy](docs/governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md) for packages, manifests, and proof of delivery. Respect task ownership and current user instructions when publication work is happening in parallel.

## Submit and deliver

Open a pull request that explains the problem, what changed, the sources you relied on, the checks you ran, and anything still unfinished. Keep unrelated formatting and renaming out of the change. Merge only after the relevant checks pass for the reviewed head and any current-main integration is resolved.

After acceptance, publish a Wiki change from a clean, refreshed main checkout with `make wiki-publish`. Run `make wiki-freshness` to check the remote pages against the current sources. Publish packages through their indexed release workflow; a file in scratch storage is not a delivered release.

Close an issue only when accepted evidence meets its remaining criteria. Missing decisions and execution records stay open. Report sensitive findings through [SECURITY.md](SECURITY.md); the [license](LICENSE.md) defines reuse rights.
