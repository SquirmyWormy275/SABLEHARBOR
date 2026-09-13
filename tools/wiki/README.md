# Wiki publication

Issue [#11](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/11) requires a supported
publication path and verification of the live Wiki. This exporter consumes the existing
`docs/wiki/` Markdown. It does not modify the reader/catalog generators, publications,
approved artwork, or source files.

## Review an export

```bash
python -m pip install -r tools/wiki/requirements.txt
python -m unittest discover -s tests/wiki
python tools/wiki/export.py --revision "$(git rev-parse HEAD)" --output /tmp/sableharbor-wiki-review
```

Use a fresh output directory outside the checkout. The output contains flattened Wiki
page names, a business sidebar, and a SHA-256 manifest. Internal Wiki links use the
flattened names; other repository links and image URLs point to the full source commit.
Fragments, query parameters, existing HTML image sizing and source status language are
preserved. Asset bytes remain in their original repository locations.

Every relative target must exist within the checkout. Markdown is parsed after conversion
to reject any remaining local links, including unsupported destination syntax. This is
local link verification; it does not establish external URL availability or GitHub's live
rendering. The export records a snapshot, and a later accepted source change requires a
new publication run.

## Publish accepted main

1. Initialize the Wiki by creating its first page on GitHub if the `.wiki.git` endpoint
   does not exist. GitHub documents this prerequisite in
   [Adding or editing wiki pages](https://docs.github.com/en/communities/documenting-your-project-with-wikis/adding-or-editing-wiki-pages).
2. Configure the Actions secret `WIKI_TOKEN` with a credential that can write to this
   repository's Wiki. Credentials are supplied through the environment and GitHub CLI's
   credential helper, never embedded in a Git remote or publication manifest. See
   [GitHub authentication](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github).
3. Run **Wiki publication** using `workflow_dispatch` on `main`. Publication is manual
   so simultaneous source/publication sessions can finish before the Wiki is updated.
   A PR only tests and uploads an export; dispatch on another branch cannot publish.
4. The workflow builds the accepted snapshot, updates the cloned Wiki, commits and pushes
   without force, clones it again, and verifies every published page hash and manifest.
   An unavailable Wiki, missing credential, failed push or mismatched bytes fails the job.
5. Review live Home, sidebar, all seven business pages, logo/chart rendering and links.
   Record the run and published revision in #11 before marking its Wiki requirement done.

The manifest identifies managed pages. Previously managed pages removed from the source
are retired on the next sync; unrelated Wiki pages remain. Matching source page names
(including the initial Home page) are replaced by the repository-controlled export.
Wiki Git history is retained. Independent edits belong in the source PR workflow.

The Wiki is initialized and has been published using existing local Git authentication.
`make wiki-publish` fetches accepted main, rejects a dirty or unaccepted checkout,
publishes without force, and verifies every page in a fresh remote clone. Its receipt
is written to `var/wiki-publication.json`. The optional Actions credential is separate;
local publication does not require adding a personal token to repository secrets.

## Complete reading edition

`reading.json` explicitly inventories 198 accepted public Markdown sources and the
source selections for all seven businesses, 23 departments/institutions/capabilities
and nine historical or cross-cutting subjects. The exporter composes their substantive
text at publication time; source documents are never edited or independently copied
into another controlling archive. Section selections fail if a heading disappears.

The export adds full reading editions, topic rooms, section navigation and source links.
Links between inventoried records stay inside the Wiki. Original source wording, status,
version and dates remain visible. Each record has an original-file SHA-256 in the
publication manifest and a link pinned to the accepted source revision. The reading
rooms include historical and conditional material: inclusion is not a new canon decision.

This edition excludes the concurrently owned legal publications and private evidence.
It does not close unresolved tax/legal execution, geographic or operational questions.
Artwork is reused by URL, retaining its approved bytes. Financial packages remain
release downloads rather than being converted into invented Markdown financial books.

To extend coverage, update the explicit inventory and source selections, run the Wiki
unit tests, export and audit the complete output, then inspect mobile and desktop
rendering. Source content is compiled afresh at the accepted main revision on every
publication. Do not edit the live Wiki independently.

## Editorial presentation and historical addresses

All 39 subject guides include a plain-language orientation, related reading and an
explicit unknowns section. Start Here, the glossary and the open-questions register
provide onboarding and a dated evidence boundary. Source text remains separately
identified in the composed in-depth reading sections.

`titles.json` assigns readable published titles without renaming repository sources.
The export rewrites navigation and retains every prior address as a compatibility page,
including its section anchors. These pages are recorded in the manifest's `aliases`;
they are not counted as additional articles. The navigation audit checks each route,
and the browser review checks the canonical reading edition.

## Detect stale publication

```bash
make wiki-freshness
```

The checker clones the live Wiki read-only, verifies its managed page bytes and compares
an export from the inspected checkout with the publication. It reuses the published
revision in URLs so unrelated code commits do not cause false drift. Source, configuration,
linked-file hashes and tracked directory trees identify changes that affect the reading
edition. Run from refreshed main when assessing the accepted source.

States are `current`, `stale`, `modified` (independent or missing remote pages),
`unverifiable` (a legacy manifest lacks input hashes), or `unavailable` (inspection
failed). Only `current` exits successfully by default. `--report-only` retains the report
without failing; it does not turn an unknown result into a verified publication.

The read-only workflow runs after main changes, daily and on manual dispatch. Its JSON
artifact and run summary show the precise differences. It does not provision credentials,
publish pages or change repository settings. After an accepted content change, publish
with `make wiki-publish` and dispatch the freshness workflow to verify the updated state.
