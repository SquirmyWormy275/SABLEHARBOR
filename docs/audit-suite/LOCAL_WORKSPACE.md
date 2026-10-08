# Local audit workspace

Run `sableharbor-workspace start` and wait for `READY`. Open CLEAN at
<http://127.0.0.1:8782> or MESSY at <http://127.0.0.1:8783>. The existing local
launcher also supports `status`, `stop` and `restart`; stopping saves the current
configuration and restarting retains both histories.

The private role credentials and workflow guide are delivered in
Downloads as `SABLEHARBOR_AUDIT_WORKSPACE_ACCESS_2026-10-07.json` and
`SABLEHARBOR_AUDIT_WORKSPACE_GUIDE_2026-10-07.md`. Credentials are kept outside Git.
`auditor` is the learner, `operator` is the instructor, and `reviewer` is the
authorized review identity. Sign out before switching roles.

The fictional scope covers corporate shared controls for 2027, SOC 2 Security,
Availability and Confidentiality, and simulated HIPAA business-associate and
subcontractor operations. The approved scenario includes operating Reno and Boise
sites and synthetic ePHI flows. Earlier 2026 planning records remain historical
planning records.

In PBC & evidence, create and issue a request for the relevant control and owner.
Open Browse company source records, choose an authorized system, link the request
and collect the exact available version. Collection reads the company original,
retains its receipt and makes the collected original available for inspection and
download. The learners have scoped access to their respective company branches.
Historic instructor snapshots retain the permissions and evidence present when
they were captured.

The delivered implementation passed the paired browser walkthrough, 114 read-only
navigation checks across both roles and desktop/mobile sizes, protected instructor
Key and offline debrief ZIP checks, and actual company-record collection and
download in both branches. Full physical comparison preserved 5,714 native versions,
business checkpoints and prior receipts while admitting exactly two new collection
receipts. Current delivery revisions are CLEAN 6011 and MESSY 6856; historic Key
revisions 6008 and 6853 are preserved.

Framework comparisons propose delta controls and procedures. Software validation
does not establish an audit opinion, certification, whole-estate evidence
completeness or learner competence. Instructor assessments retain their recorded
limitations and selected versions.

## Development and source maintenance

The regression tests use their checkout's source tree and temporary owned company
fixtures. They do not require this workstation's credentials or current audit
data. Historical observation-counter and preexpiry-producer checks require their
separately preserved inputs and report skips when those inputs are unavailable.
Set `SABLEHARBOR_HISTORICAL_PRODUCER` to an available preserved producer checkout
to exercise that historical conversion. Current managed-history, authority,
collection and Key checks run against owned fixtures in an ordinary checkout.

Retained histories admit exact runtime source bytes. The finite modules listed
in `REVIEWED_RUNTIME_SOURCE_PINS.json` therefore retain their reviewed formatting;
`scripts/check_audit_runtime_sources.py` checks their SHA-256 pins and Python
syntax in required CI. Other source, tests and launcher tooling use the normal
Ruff checks. Changing a listed runtime module requires an explicit source-pin
successor and the applicable domain tests; automatic style cleanup must not
silently change a retained history's runtime admission.
