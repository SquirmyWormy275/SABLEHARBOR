# Wiki Publication Source

`docs/wiki/` is the version-controlled source for the Sable Harbor GitHub wiki. Repository canon, organization, brand, and accepted data releases remain authoritative; wiki pages summarize and link to them.

## Publication state

At the September 1, 2026 audit, the repository reported `has_wiki: false`. The source package is complete enough for review, but publication requires the repository owner to enable the wiki and then copy these Markdown files into the separate `SABLEHARBOR.wiki.git` repository.

## Controlled publication

After this portal PR is accepted and the wiki is enabled:

```bash
git clone https://github.com/SquirmyWormy275/SABLEHARBOR.wiki.git
rsync -av --delete docs/wiki/ SABLEHARBOR.wiki/ --exclude README.md --exclude PUBLISH_STATUS.md
cd SABLEHARBOR.wiki
git add -A
git commit -m "Publish Sable Harbor enterprise wiki"
git push
```

Before publishing, run `python scripts/validate_enterprise_portal.py`. Never publish release-candidate quantitative claims as accepted facts.
