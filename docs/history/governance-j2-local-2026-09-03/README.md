# September 3 governance and J2 local-branch history

**Status:** historical, unaccepted local branch source. These bytes do not change current canon, board authority, J2 appointments, publication status, or the accepted source-locked PDFs. Use the current [governance guide](../../governance/README.md), [J2 guide](../../j2/README.md), and [canon](../../canon/) for controlling decisions.

Four local workstation commits from 2026-09-03 introduced or repeated 138 distinct Git blobs that were absent from accepted public main and every current public branch or tag at intake. The [machine-readable manifest](MANIFEST.json) records each original path, byte size, SHA-256, Git blob OID, commit, source date, current-path Git blob OID where a path still exists, and authority. The package contains 129 `docs/` blobs, four `scripts/` blobs, three `tools/` blobs, one root README blob, and one workflow blob. Seventy-six of the document blobs are generated PDFs; their source Markdown and accepted board/canon records outrank them.

| Local commit | Historical stage | Distinct exported blobs |
| --- | --- | ---: |
| `89cc0a2f1711839d115f6b18a0c1a2659ac42533` | Integrate governance, J2 and Alexandria canon | 43 |
| `a1113da8add1aad755dde578723026b06bde25f4` | Expand Phase 2 governance and J2 doctrine coverage | 58 |
| `626db32ae72c6058de5f84eb02cc292574388cec` | Complete governance publication and repository hygiene | 35 |
| `c6ff7b017c3ec48029bf991abfc148281ae54b63` | Complete constitutional doctrine and Alexandria catalog | 2 |

The exact source bytes are grouped by original domain and Git blob OID in the historical [GitHub Release](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/governance-j2-local-history-2026-09-03). Asset: `sableharbor-governance-j2-local-history-2026-09-03.zip`, 3,426,574 bytes, SHA-256 `4fe5db5ff13ab9fcbe395be54fac742962a040e418b6ea041aa86ce5b2e541eb`. Run `python docs/history/governance-j2-local-2026-09-03/verify.py <downloaded-asset>`; it checks the outer hash and every original byte, SHA-256, Git blob OID, length and package path. The original blobs were not edited; only deterministic ZIP member paths and metadata were added during packaging on 2026-10-23.

This is a **filtered export of unique changed blobs**, not a full Git bundle or full four-commit tree. The original local commits and worktrees remain protected until their parent/ref relationships, dirty files, and other historical branches receive separate dispositions. Automated text and PDF extraction screening found no email, credential, private-contact or hidden-evaluator-key terms in these 138 blobs; this screening does not promote any historical assertion. No local cleanup clearance follows from this package alone.
