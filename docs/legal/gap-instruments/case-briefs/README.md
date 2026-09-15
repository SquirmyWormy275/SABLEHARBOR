# Choose a case and start working

Each brief is one printed page: situation, question, exact files and deliverable. These are public learning materials; new designs remain draft for exact-file review.

- **Account for the ARU acquisition** — [brief](SH-CASE-ARU-01.md) · [letterhead PDF](SH-CASE-ARU-01.pdf) · [browser view](SH-CASE-ARU-01.html)
- **Resolve a disputed Foundry Field invoice** — [brief](SH-CASE-FF-01.md) · [letterhead PDF](SH-CASE-FF-01.pdf) · [browser view](SH-CASE-FF-01.html)
- **Trace the Red Wash closure obligation** — [brief](SH-CASE-RW-01.md) · [letterhead PDF](SH-CASE-RW-01.pdf) · [browser view](SH-CASE-RW-01.html)
- **Practice five separate reconciliations** — [brief](SH-CASE-RECON-01.md) · [letterhead PDF](SH-CASE-RECON-01.pdf) · [browser view](SH-CASE-RECON-01.html)
- **Close one ARU reporting period** — [brief](SH-CASE-CLOSE-01.md) · [letterhead PDF](SH-CASE-CLOSE-01.pdf) · [browser view](SH-CASE-CLOSE-01.html)

After completing a case, use [evidence tracking](../evidence-tracking/README.md) to record incomplete or disputed support. [Source-impact reporting](../source-impact/README.md) identifies dependent work requiring recheck when sources change. [The release index](../REVIEW_RELEASES.md) provides the portable review package.

The [structured source](source.json) and [SQLite index](case-briefs.sqlite3) preserve every brief and file instruction. Reproduce with `python tools/legal_gaps/case_briefs.py build`; validate with `python tools/legal_gaps/case_briefs.py validate`. Existing letterhead and logo are reused unchanged.
