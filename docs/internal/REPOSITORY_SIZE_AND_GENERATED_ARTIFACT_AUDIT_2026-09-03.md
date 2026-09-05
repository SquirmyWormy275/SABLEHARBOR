# Repository Size and Generated-Artifact Audit — 2026-09-03

**Status:** COMPLETE — no deletion recommended

Commands run: `git count-objects -vH`; `git rev-list --objects --all | sort -k 2`; and `find docs assets -type f \( -name '*.pdf' -o -name '*.png' -o -name '*.sqlite3' -o -name '*.zip' \) -print -exec du -h {} \;`.

Git storage is 22.73 MiB packed (3,101 packed objects), with no garbage. The largest reviewed in-scope artifacts are the J2 A4 and US-Letter PDFs (5.9 MiB and 5.7 MiB), the brand ZIP (2.6 MiB), the organization briefing ZIP (1.4 MiB), the J2 primary PNG (740 KiB), and the institutional SQLite catalog (520 KiB). Other controlled PDFs and renders are materially smaller.

| Class | Representative paths | Disposition |
|---|---|---|
| Canonical Markdown source | `docs/governance/`, `docs/j2/`, `docs/controls/`, `docs/organization/` | Keep in-tree; authority source |
| Generated controlled publication | `docs/governance/publications/*.pdf`, `docs/j2/publications/*.pdf` | Keep in-tree; monitor reproducibility |
| Generated JSON/SQLite catalog | `docs/internal/institutional_catalog.json`, `docs/internal/institutional_catalog.sqlite3` | Keep in-tree; regenerate from source/manifest |
| SVG/PNG chart asset | `docs/organization/assets/`, `docs/organization/briefing/images/` | Keep SVG/source and current renders; monitor |
| Approved J2 identity source asset | `assets/brand/logos/j2__*.png` | Keep in-tree; PNG is the approved source-artwork exception |
| Distributable ZIP package | `assets/brand/packages/*.zip`, `docs/organization/briefing/*.zip` | Keep for current release; consider release assets later if growth warrants |
| Convenience render | letterhead PNGs and briefing preview/render files | Keep while useful; move to releases later if repository growth warrants |

`MAINTAINERS.md` adequately defines canonical Markdown authority, generated PDF and JSON/SQLite boundaries, manifest/checksum treatment, chart rendering, the J2 PNG source-artwork exception, wiki summary status, and the rule that generated artifacts cannot independently create canon.
