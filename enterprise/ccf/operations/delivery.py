"""One verified build for CCF workflow, signed API rehearsal and assessment handoff."""

import argparse
import csv
import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from enterprise.ccf.assurance import assessment_run
from enterprise.ccf.registry import compile_registry, digest

from . import examples, migration, rehearsal, store, testing

GATES = [
    dict(
        id="IDENTITY",
        blocks="Enterprise sign-in",
        required=[
            "Exact issuer and API audience",
            "Provider-specific access-token purpose claim",
            "Reviewed public signing keys and rotation procedure",
            "Issuer/subject bindings to authorized local principals",
        ],
    ),
    dict(
        id="DEPLOYMENT",
        blocks="Live service activation",
        required=[
            "Approved host, private network exposure and DNS name",
            "TLS certificate/reverse-proxy configuration",
            "Named service operator, protected storage and backup/cutover plan",
            "Nginx configuration validation on target host",
        ],
    ),
    dict(
        id="SOURCE_ACCESS",
        blocks="Live automated evidence collection",
        required=[
            "First authoritative source-system endpoints or exports",
            "Approved read scopes and privately delivered credentials",
            "Provider field translation verified against original records",
            "Independent population extraction and exclusion authority",
        ],
    ),
    dict(
        id="OPERATING_SCOPE",
        blocks="Actual operating assessment",
        required=[
            "Named owners and independent reviewers",
            "Actual service, system, vendor and PHI responsibility facts",
            "Operating period and implementation versions",
            "Approved commitments and test criteria",
        ],
    ),
    dict(
        id="QUALIFIED_REVIEW",
        blocks="External assessment and customer assurance",
        required=[
            "Qualified source/context and exact mapping acceptance",
            "Framework-specific scope and independence review",
            "Resolved findings or explicitly accepted disclosures",
            "Assessor engagement and authorized customer-facing statements",
        ],
    ),
]


def handoff(reference, plans, report):
    rows = []
    for pid, p in sorted(plans.items()):
        related = [g for g in report["period_results"].values() if g["plan_id"] == pid]
        rows.append(
            dict(
                plan_id=pid,
                control_id=p["control_id"],
                boundary_id=p["boundary_id"],
                adapter=p["adapter"] or "MANUAL",
                mandatory_manual_criteria=len(p["criteria"]),
                exercise_periods=len(related),
                synthetic_failures=sum(g["result"] == "FAIL" for g in related),
                actual_coverage="NOT_ASSERTED",
                mapping_acceptance="UNRESOLVED",
            )
        )
    return dict(
        schema_version=1,
        status="ASSESSMENT_PREPARATION_NOT_EXTERNAL_ASSURANCE",
        reference_digest=digest(reference),
        rows=rows,
        source_dependencies=reference["source_dependencies"],
        framework_deltas=reference["variant_comparisons"],
        required_live_inputs=[
            dict(g, status="MISSING_ACTUAL_INPUTS", supplied_records=[]) for g in GATES
        ],
        qualified_assessment_interface="enterprise.ccf.assurance build --catalog <qualified-catalog.json> --assessment <reviewed-assessment.json> --source-root <authorized-originals> --output <new-private-output>",
        limitation="Workflow tests and fixture reviews do not accept normative mappings or certify a service. Existing strict assurance-engine inputs remain the external coverage gate.",
    )


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")
    path.chmod(0o600)


def build(reference_path, source_root, output, legacy_store=None, legacy_revision=None):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Delivery requires a new private directory")
    if bool(legacy_store) != bool(legacy_revision):
        raise ValueError("History migration requires both store and trusted legacy revision")
    assessment_run.verify(reference_path, compile_registry(), source_root)
    reference = json.loads((Path(reference_path) / "ASSESSMENT_RUN.json").read_text())
    plans = testing.plans(reference)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ccf-delivery-", dir=output.parent) as tmp:
        staged = Path(tmp) / "bundle"
        staged.mkdir(mode=0o700)
        summary = examples.build(staged / "control-exercise", plans)
        integration = rehearsal.run(staged / "integrated-rehearsal", plans)
        report = json.loads((staged / "control-exercise/ASSESSMENT_REPORT.json").read_text())
        packet = handoff(reference, plans, report)
        write(staged / "REFERENCE_ASSESSMENT.json", reference)
        write(staged / "ASSESSMENT_HANDOFF.json", packet)
        write(staged / "ACTIVATION_INPUTS.json", packet["required_live_inputs"])
        write(staged / "SOURCE_DEPENDENCIES.json", packet["source_dependencies"])
        write(staged / "FRAMEWORK_DELTAS.json", packet["framework_deltas"])
        with (staged / "CONTROL_COVERAGE.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(packet["rows"][0]))
            writer.writeheader()
            writer.writerows(packet["rows"])
        migrated = None
        if legacy_store:
            migrated = migration.migrate(
                Path(legacy_store), staged / "migrated-history", legacy_revision
            )
        gate_text = "\n\n".join(
            "## "
            + g["id"]
            + " — "
            + g["blocks"]
            + "\n\n"
            + "\n".join("- " + x for x in g["required"])
            for g in GATES
        )
        (staged / "ACTIVATION_INPUTS.md").write_text(
            "# Live activation inputs\n\nThe approved reference scope is retained. These inputs are needed to activate actual integrations and accept assurance; no new scope approval is inferred.\n\n"
            + gate_text
            + "\n"
        )
        delta_rows = "\n".join(
            f"| {name} | {len(r['additional_candidate_control_ids'])} | {len(r['additional_action_ids'])} |"
            for name, r in packet["framework_deltas"].items()
        )
        (staged / "START_HERE.md").write_text(
            "# Integrated CCF delivery\n\n"
            "[Assessment handoff](ASSESSMENT_HANDOFF.json) · [Control coverage](CONTROL_COVERAGE.csv) · [Live inputs](ACTIVATION_INPUTS.md) · [Source dependencies](SOURCE_DEPENDENCIES.json) · [Signed API rehearsal](integrated-rehearsal/INTEGRATION_RESULT.json) · [Control exercise](control-exercise/START_HERE.md)\n\n"
            f"{len(plans)} plans cover {summary['baseline_controls']} baseline controls across the three approved reference boundaries. {summary['automated_controls']} controls have bounded automated assertions alongside mandatory human tests; the remaining {summary['manual_only_controls']} use manual tests. {summary['cases']} synthetic cases exercise substantive failures, retests and prospective correction.\n\n"
            "The integrated rehearsal uses real loopback HTTP requests, signed fixture identities, independently supplied population records, scheduled collection, missing-manual-test findings and independent correction review. It does not connect to an actual identity provider or source account.\n\n"
            "| Selection | Additional candidate controls | Additional work items |\n|---|---:|---:|\n"
            + delta_rows
            + "\n\n"
            "The API, collector, scheduler and expanded tests are implemented. Deployment templates and private migration receipts are supplied; no live service has been deployed. Licensed source/context review, operating facts and qualified coverage acceptance remain explicit inputs. No output is an assessor opinion or customer assurance claim.\n\n"
            + (
                "[Verified prior history migration](migrated-history/MIGRATION_RECEIPT.json) retains original records, credentials, permissions and failures in a separate private copy. Quiesce the old writer before actual cutover.\n"
                if migrated
                else "Prior stores can be copied with the verified migration command using their trusted historical evaluator revision.\n"
            )
        )
        stats = dict(
            plans=len(plans),
            automated_controls=summary["automated_controls"],
            manual_only_controls=summary["manual_only_controls"],
            synthetic_cases=summary["cases"],
            signed_api_rehearsal=integration["status"],
            source_reperformance="PASS",
            history_migration="PASS" if migrated else "NOT_REQUESTED",
            actual_coverage="NOT_ASSERTED",
        )
        write(staged / "DELIVERY_RESULT.json", stats)
        for p in staged.rglob("*"):
            p.chmod(0o700 if p.is_dir() else 0o600)
        manifest = {
            str(p.relative_to(staged)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(staged.rglob("*"))
            if p.is_file()
        }
        write(staged / "DELIVERY_MANIFEST.json", dict(files=manifest))
        staged.rename(output)
    return stats


def verify(output):
    output = Path(output)
    if output.is_symlink() or any(p.is_symlink() for p in output.rglob("*")):
        raise ValueError("Delivery cannot contain symlinks")
    manifest = json.loads((output / "DELIVERY_MANIFEST.json").read_text())["files"]
    observed = {
        str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.rglob("*"))
        if p.is_file() and p != output / "DELIVERY_MANIFEST.json"
    }
    if manifest != observed:
        raise ValueError("Delivery file/hash mismatch")
    for relative in (
        "control-exercise/workflow.sqlite3",
        "integrated-rehearsal/workflow.sqlite3",
        "migrated-history/workflow.sqlite3",
    ):
        path = output / relative
        if path.exists():
            db = store.connect(path)
            try:
                store.replay(db)
            finally:
                db.close()
    reference = json.loads((output / "REFERENCE_ASSESSMENT.json").read_text())
    reported = json.loads((output / "control-exercise/ASSESSMENT_REPORT.json").read_text())
    db = store.connect(output / "control-exercise/workflow.sqlite3")
    try:
        with patch.object(store, "now", return_value=reported["as_of"]):
            reproduced = store.report_as(db, "DEMO-REVIEWER")
        if reproduced != reported:
            raise ValueError("Control report differs from retained history")
    finally:
        db.close()
    expected = handoff(reference, testing.plans(reference), reproduced)
    if expected != json.loads((output / "ASSESSMENT_HANDOFF.json").read_text()):
        raise ValueError("Assessment handoff differs from re-performance")
    return dict(
        verified=True,
        scope="File integrity and current evaluator history replay; not source acceptance or authenticity against a privileged filesystem administrator",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--reference")
    parser.add_argument("--source-root")
    parser.add_argument("--legacy-store")
    parser.add_argument("--legacy-revision")
    args = parser.parse_args()
    try:
        if args.command == "build":
            if not args.reference or not args.source_root:
                raise ValueError("Build requires verified reference and original source root")
            result = build(
                args.reference,
                args.source_root,
                args.output,
                args.legacy_store,
                args.legacy_revision,
            )
        else:
            result = verify(args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"CCF delivery error: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
