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

As of September 12, 2026, the Wiki clone endpoint returns “Repository not found” and
no Actions secrets are configured. This implementation alone does not claim live
publication, credential provisioning or completion of #11.
