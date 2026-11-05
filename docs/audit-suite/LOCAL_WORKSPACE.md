# Local audit workspace

To read the actual company data from a cloud environment or ordinary repository
clone, open the [5,714-version source library](company-records/README.md) or the
[November client submissions](demo-2026-11/client-records/README.md). Neither
requires this local workspace or an external drive. The instructions below are
for running the separate auditor workrooms.

## Run CLEAN and MESSY from a checkout

An ordinary clone can run its own CLEAN and MESSY workrooms on Linux. You need
Python 3.11 or later, `uv`, `make` and Node 22.12 or later. Uploading files for
document inspection also needs Bubblewrap (`bwrap`); collecting company records
does not. From the repository root:

```sh
make bootstrap                 # uv sync --frozen --all-extras
make audit-workspace-web       # npm ci and npm run build in audit_suite_web
make audit-workspace-setup     # verify and import the company records, provision roles
make audit-workspace-start     # wait for "status": "READY"
```

Open CLEAN at <http://127.0.0.1:8782> and MESSY at <http://127.0.0.1:8783>.
Both servers bind only to loopback and use local HTTP. Setup takes a few minutes
because it imports every source version one at a time. It writes everything to the
Git-ignored `var/audit-workspace` directory (set `SABLEHARBOR_WORKSPACE_ROOT` to
use another private directory):

- CLEAN imports company [history 01](company-records/history-01/) (branch
  `HARBOR-OPERATIONS-A`, 2,793 versions in 447 systems). MESSY imports
  [history 02](company-records/history-02/) (branch `HARBOR-OPERATIONS-B`, 2,921
  versions in 475 systems). Each keeps the native company, branch, system,
  record, version, owner, business-event and availability times and provenance
  in its own company store.
- Each mode has its own engagement history and one SOC 2 Type 2 engagement for
  2027, bound to its branch and already activated for company-source collection.
  The simulation date is 1 January 2028.
- Each mode has `operator` (instructor), `auditor` (learner) and `reviewer`
  credentials in `var/audit-workspace/credentials/<mode>-<role>.json`, for example
  `clean-auditor.json`. Paste the file's `credential` value into the sign-in form,
  or send it as `Authorization: Bearer <credential>` to the HTTP API. Credentials
  last 30 days; `make audit-workspace-credentials` revokes them and issues new ones
  with the same access.

`make audit-workspace-status`, `make audit-workspace-stop` and
`make audit-workspace-restart` manage the two servers. Stopping and restarting
keeps both histories. Server logs are in `var/audit-workspace/logs`. The make
targets call `uv run python -m tools.audit_suite.workspace_launcher`; run it with
`--help` for the options.

A typical engagement:

1. Sign in as the auditor and open the engagement. In **Kickoff & scope**, choose
   **Begin kickoff meeting**.
2. In **PBC & evidence**, choose **New PBC request +** and give the boundary,
   control, evidence owner, purpose and dates. Open the request and choose
   **Issue initial request**.
3. Open **Browse company source records**, choose a system, link the issued
   request and choose **Collect this version**. The collected original appears
   under **Original evidence files** with **Download original**; its bytes match
   the file in `company-records`.
4. In **Populations & samples**, open **Collect a source-record census**, load the
   systems, choose one with an event window inside 2027 and the issued request,
   and collect it. Tick the review statement, choose **Import reviewed census as
   provisional**, then **Make selection** to draw a sample.
5. In **Workpapers & review**, choose **New structured workpaper**, cite the
   collected artifact ID as evidence, then **Export for human review** and
   download the package.
6. Sign out and sign in as the reviewer to review the workpaper, or as the
   operator to see the instructor view.

These workrooms connect the company records only. Generated scenarios, the
instructor answer library, local inference and voice need the separately
delivered private corpus and runtime described in the
[workroom README](../../audit_suite_web/README.md); they remain unavailable here.

## The configured workstation installation

The original installation runs on the author's configured workstation. Its
`sableharbor-workspace` command (`tools/audit_suite/local_workspace/workspace.py`)
starts only a privately admitted release with retained histories, a pinned Python
interpreter and private role credentials, none of which a clone contains. On that
workstation, run `sableharbor-workspace start` and wait for `READY`; CLEAN and
MESSY use the same two addresses. That launcher also supports `status`, `stop`
and `restart`; stopping saves the current configuration and restarting retains
both histories.

The private role credentials and workflow guide are delivered separately on the
configured workstation. Use the latest dated access file referenced by the
private guide; credentials expire and are kept outside Git.
`auditor` is the learner, `operator` is the instructor, and `reviewer` is the
authorized review identity. Sign out before switching roles.

The installed pair was [recovered on 20 October 2026](LOCAL_RECOVERY_2026-10-20.md)
after an interrupted shutdown. The [23 October successor](LOCAL_RECOVERY_2026-10-23.md)
records the later separate histories at CLEAN 6012 and MESSY 6857, the actual
stop/restart and download evidence, and the remaining operational limits.
On the workstation, check `sableharbor-workspace status` before use.
If it reports `RECONCILIATION_REQUIRED`, preserve and inspect the current
session rather than resetting either history. For a repository-based audit
software test that does not need any workroom, use the
[verified CLEAN/MESSY company records](CLEAN_MESSY_INTAKE.md).

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

The earlier delivery passed the paired browser walkthrough, 114 read-only
navigation checks across both roles and desktop/mobile sizes, protected instructor
Key and offline debrief ZIP checks, and actual company-record collection and
download in both branches. Full physical comparison preserved 5,714 native versions,
business checkpoints and prior receipts while admitting exactly two new collection
receipts. That delivery recorded CLEAN 6011 and MESSY 6856; historic Key
revisions 6008 and 6853 are preserved. The later revision and backup evidence is
recorded in the dated successor above.

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

Tests listed in `tests/audit_suite/private_replay_modules.json` reconstruct exact
historical private authoring runs or the separately reviewed full-program pack.
They are reported as skipped in ordinary checkouts. To run those historical
integration checks with preserved inputs, set `SABLEHARBOR_RUN_PRIVATE_REPLAYS=1`
and, where needed, `SABLEHARBOR_PRIVATE_REPLAY_ROOT` to their private source root.
This does not grant audit credit or replace current company-original collection.
CI builds both native helpers explicitly and runs the portable regressions across
eight isolated shards, including their standard-library fallback cases.

Retained histories admit exact runtime source bytes. The finite modules listed
in `REVIEWED_RUNTIME_SOURCE_PINS.json` therefore retain their reviewed formatting;
`scripts/check_audit_runtime_sources.py` checks their SHA-256 pins and Python
syntax in required CI. Other source, tests and launcher tooling use the normal
Ruff checks. Changing a listed runtime module requires an explicit source-pin
successor and the applicable domain tests; automatic style cleanup must not
silently change a retained history's runtime admission.

## November company-source edition

The separate [November source delivery](demo-2026-11/SOURCE_DELIVERY.md) supplies
selected company records through verified files. Its [scope](demo-2026-11/SCOPE.md)
describes the local records and dates. Preparing or replaying that isolated edition
does not reset either workroom or require an auditor-product implementation.
