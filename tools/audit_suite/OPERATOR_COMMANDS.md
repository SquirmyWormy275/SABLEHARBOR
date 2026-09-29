# Local operator commands

Run from the repository root after installing the project's `audit-suite` Python extra and the separately authorized private source bundle. These tools contain no private scenarios, answers, credentials, or random-seed override. Source installation is described by `private_source_bundle.py --help`.

The examples below use the repository's ignored generated directory. Create a new private output directory; existing outputs and demo stores are never overwritten.

```bash
mkdir -m 700 enterprise/generated/audit-suite/operator-run
uv run --extra audit-suite python tools/audit_suite/operator.py validate-config \
  --mode CLEAN --configuration tools/audit_suite/examples/clean.json
uv run --extra audit-suite python tools/audit_suite/operator.py validate-corpus \
  --corpus-root enterprise/generated/audit-suite/private-corpus \
  --report enterprise/generated/audit-suite/operator-run/corpus-validation.json
uv run --extra audit-suite python tools/audit_suite/operator.py demo \
  --corpus-root enterprise/generated/audit-suite/private-corpus \
  --private-root enterprise/generated/audit-suite/operator-run/state \
  --credentials enterprise/generated/audit-suite/operator-run/credentials.json \
  --receipt enterprise/generated/audit-suite/operator-run/demo.json
```

`demo` seeds a new **clean** engagement with actual Engine commands: configuration/scope validation, source generation, kickoff, issued PBC request, clock advancement, native evidence receipt, a limited workpaper, and review by a separate principal. It makes no model calls. Credentials are written only to the private credential file; do not put that file into a review package. The default is one canonical control in a supported 2027 reference period; `--control`, `--period-start`, `--period-end`, and `--timezone` can select another supported scope. Historical owner/source gaps cause failure rather than invented appointments.

Read `learner_id`, `reviewer_id`, and `engagement_id` from the private `demo.json` receipt. Substitute the learner ID and engagement ID below for a human evidence package:

```bash
uv run --extra audit-suite python tools/audit_suite/operator.py export-review \
  --corpus-root enterprise/generated/audit-suite/private-corpus \
  --private-root enterprise/generated/audit-suite/operator-run/state \
  --principal LEARNER_ID --engagement ENGAGEMENT_ID --edition EVIDENCE \
  --output enterprise/generated/audit-suite/operator-run/evidence-review.zip
```

For a private instructor/reviewer appendix, use the explicitly granted reviewer ID and `--edition REVIEWER`, with a different private output filename. Export does not grant privileges or infer an actor. The command returns the retained ZIP's SHA256 and byte count. This is a local operator capability requiring filesystem access, not a public authentication shortcut or web API.

`validate-config` checks configuration syntax and allocation constraints; it does not establish source or scope applicability. `validate-corpus` checks every canonical obligation, installed optional source edition, and clean control. It uses period-valid organizational bindings, renders native records, and checks bounded authored event paths. Explicit manual path intentions are retained as metadata; they do not execute inquiry, release records, or establish an audit conclusion. Detailed results remain in the private report. `REVIEW_REQUIRED` records (for example, intentionally historical dates) remain explicit; they are not professional acceptance. Structural/render/path failures produce a nonzero exit code. These checks do not replace actual full engagement exercises, human rubric review, or assessment of completeness and operating effectiveness.

All commands emit short status JSON and nonzero exit status on failure. No hosted deployment, publication, external message, or Atlas write occurs.
