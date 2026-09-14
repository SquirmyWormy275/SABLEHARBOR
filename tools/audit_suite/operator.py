"""Generic local operator checks; requires separately installed private sources."""

from __future__ import annotations

# ruff: noqa: E402
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from enterprise.audit_suite import generation
from enterprise.audit_suite.configuration import validate_configuration
from enterprise.audit_suite.corpus import Corpus, obligations, validate_bound_variant
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.store import DomainError, digest


def read_json(path):
    if path.is_symlink() or path.stat().st_size > 2_000_000:
        raise DomainError("Input must be a bounded regular JSON file")
    return json.loads(path.read_text())


def private_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.is_symlink() or path.parent.stat().st_mode & 0o077:
        raise DomainError("Output parent must be a private mode-0700 directory")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def corpus_check(args):
    from enterprise.audit_suite.artifacts import render
    from enterprise.audit_suite.clean import build_control
    from enterprise.audit_suite.organization import snapshot
    from enterprise.ccf.registry import compile_registry

    if not args.corpus_root.is_dir():
        raise DomainError("Install the authorized private source bundle first")
    corpus = Corpus(args.corpus_root)
    org = snapshot(args.repository, as_of=args.period_start)
    names = {
        p["person_id"]: p.get("name", p.get("display_name", p["person_id"]))
        for p in org["canonical_people"] + org["proposed_people"]
    }
    assignments = {a["control_id"]: a for a in org["control_assignments"]}
    scope = {
        "period_start": args.period_start,
        "period_end": args.period_end,
        "timezone": args.timezone,
        "boundary_id": "corporate",
        "temporal_basis": "PERIOD",
        "repository": str(args.repository),
        "owner_names": names,
    }
    results = []
    definitions = []
    for variant_id in obligations():
        try:
            definitions.append(("CANONICAL", corpus.load(variant_id)))
        except (DomainError, ValueError, KeyError, TypeError) as exc:
            results.append(
                {"id": variant_id, "edition": "CANONICAL", "status": "FAIL", "error": str(exc)}
            )
    # The canonical obligation count remains unchanged by optional authority editions.
    for path in sorted((args.corpus_root / "authority-editions/REAL_SOURCE").glob("*.json")):
        try:
            value = read_json(path)
            canonical = corpus.load(value["id"])
            corpus.select(
                canonical["option_id"],
                b"operator-authority-validation",
                discipline=value["disciplines"][0],
                control_ids=set(value["binding_contract"]["applicable_control_ids"]),
                parameters={"type": "REAL_SOURCE"},
            )
            definitions.append(("REAL_SOURCE", value))
        except (DomainError, ValueError, KeyError, TypeError) as exc:
            results.append(
                {"id": path.stem, "edition": "REAL_SOURCE", "status": "FAIL", "error": str(exc)}
            )
    for edition, value in definitions:
        try:
            cid = value["binding_contract"]["applicable_control_ids"][0]
            assignment = assignments[cid]
            bindings = {
                "control_id": cid,
                "boundary": "corporate",
                "period_start": args.period_start,
                "period_end": args.period_end,
                "owner": names[assignment["primary_person_id"]],
                "reviewer": names[assignment["operating_reviewer_person_id"]],
                "custodian": names[assignment["custodian_person_id"]],
            }
            result = validate_bound_variant(value, bindings, scope)
            results.append({"id": value["id"], "edition": edition, **result})
        except (DomainError, ValueError, KeyError, TypeError) as exc:
            results.append(
                {"id": value["id"], "edition": edition, "status": "FAIL", "error": str(exc)}
            )
    clean_results = []
    for control in compile_registry(args.repository)["records"]:
        if control["kind"] != "control":
            continue
        try:
            plan = build_control(
                control, assignments[control["id"]], scope, private_root=args.corpus_root / "clean"
            )
            files = []
            for request in plan["requests"]:
                for artifact in request["artifact_recipes"]:
                    data, media = render(artifact["recipe"])
                    files.append(
                        {
                            "name": artifact["name"],
                            "sha256": hashlib.sha256(data).hexdigest(),
                            "bytes": len(data),
                            "media_type": media,
                        }
                    )
            clean_results.append({"id": control["id"], "status": "PASS", "files": files})
        except (DomainError, ValueError, KeyError, TypeError) as exc:
            clean_results.append({"id": control["id"], "status": "FAIL", "error": str(exc)})
    failures = sum(r["status"] == "FAIL" for r in results + clean_results)
    report = {
        "status": "FAIL" if failures else "PASS_BOUNDED_SOURCE_VALIDATION",
        "canonical_required": len(obligations()),
        "canonical_validated": sum(
            r["edition"] == "CANONICAL" and r["status"] != "FAIL" for r in results
        ),
        "authority_editions": sum(r["edition"] == "REAL_SOURCE" for r in results),
        "clean_controls": len(clean_results),
        "failures": failures,
        "review_required": sum(r["status"] == "REVIEW_REQUIRED" for r in results),
        "professional_validation": "NOT_ASSERTED",
        "full_engine_playthrough": "NOT_RUN_BY_THIS_COMMAND",
        "results": results,
        "clean_results": clean_results,
    }
    private_write(args.report, report)
    return {
        k: report[k]
        for k in [
            "status",
            "canonical_required",
            "canonical_validated",
            "authority_editions",
            "clean_controls",
            "failures",
            "review_required",
        ]
    }, bool(failures)


def submit(engine, actor, state, kind, payload):
    return engine.command(
        actor,
        state["id"],
        {
            "command_id": "operator-" + kind + "-" + str(state["revision"]),
            "expected_revision": state["revision"],
            "kind": kind,
            "payload": payload,
        },
    )


def demo(args):
    if args.private_root.exists():
        raise DomainError("Demo requires a new isolated private root")
    if not args.corpus_root.is_dir():
        raise DomainError("Install authorized private sources before building the demo")
    engine = Engine(args.private_root, repository=args.repository, corpus_root=args.corpus_root)
    learner = engine.store.provision("Local demo learner", ["learner"])
    reviewer = engine.store.provision("Local demo reviewer", ["reviewer"])
    private_write(args.credentials, {"learner": learner, "reviewer": reviewer})
    scope = {
        "programs": ["SOC2"],
        "report_type": "Type 2",
        "period_start": args.period_start,
        "period_end": args.period_end,
        "timezone": args.timezone,
        "boundaries": ["corporate"],
        "control_ids": [args.control],
    }
    state = engine.create(
        learner["id"],
        {
            "command_id": "operator-demo",
            "title": "Local clean workflow demonstration",
            "discipline": "IT",
            "mode": "CLEAN",
            "scope": scope,
            "configuration": {"selections": []},
        },
    )
    state = submit(engine, learner["id"], state, "scenario.validate", {})
    if state["generation"]["state"] != "VALIDATED":
        raise DomainError("Demo scope/source validation failed; inspect the private store")
    state = submit(engine, learner["id"], state, "scenario.build", {})
    for _ in range(1000):
        if state["phase"] != "GENERATING":
            break
        state = generation.step(engine, learner["id"], state["id"])
    if state["phase"] != "READY":
        raise DomainError("Demo generation did not reach READY")
    state = submit(engine, learner["id"], state, "kickoff.start", {})
    request = state["requests"][0]
    state = submit(engine, learner["id"], state, "pbc.issue", {"request_id": request["id"]})
    state = submit(engine, learner["id"], state, "clock.advance", {"mode": "ONE_BUSINESS_DAY"})
    evidence = [a["id"] for a in state["artifacts"] if a["status"] == "AVAILABLE"]
    if not evidence:
        raise DomainError("No demonstration support arrived; inspect source availability")
    state = submit(
        engine,
        learner["id"],
        state,
        "workpaper.add",
        {
            "control_id": args.control,
            "title": "Operator demonstration workpaper",
            "text": (
                "Received native supporting files. This demonstration does not establish "
                "population completeness or control effectiveness."
            ),
            "evidence_ids": evidence,
            "conclusion": "LIMITATION",
        },
    )
    engine.store.grant(state["id"], reviewer["id"], "review")
    state = submit(
        engine,
        reviewer["id"],
        state,
        "review.comment",
        {
            "workpaper_id": state["workpapers"][-1]["id"],
            "comment": "Independent demo review retains the stated limitation.",
        },
    )
    receipt = {
        "status": "PASS_DEMO_WORKFLOW",
        "engagement_id": state["id"],
        "learner_id": learner["id"],
        "reviewer_id": reviewer["id"],
        "private_root": str(args.private_root.resolve()),
        "native_artifacts": len(evidence),
        "history_head": engine.store.history(learner["id"], state["id"])[-1]["hash"],
        "professional_validation": "NOT_ASSERTED",
    }
    private_write(args.receipt, receipt)
    return {k: receipt[k] for k in ["status", "engagement_id", "native_artifacts"]}, False


def export_review(args):
    from enterprise.audit_suite.store import Store

    store = Store(args.private_root)
    # No principal IDs are inferred and no membership is granted by export.
    store.get(args.principal, args.engagement)
    engine = Engine(args.private_root, repository=args.repository, corpus_root=args.corpus_root)
    state = engine.get(args.principal, args.engagement)
    state = submit(engine, args.principal, state, "review.export", {"edition": args.edition})
    artifact = next(a for a in reversed(state["artifacts"]) if a.get("edition") == args.edition)
    data = engine.artifacts.read(artifact)
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if args.output.parent.is_symlink() or args.output.parent.stat().st_mode & 0o077:
        raise DomainError("Export destination parent must be private mode0700")
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
    return {
        "status": "PASS_REVIEW_EXPORT",
        "edition": args.edition,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }, False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=REPOSITORY)
    commands = parser.add_subparsers(dest="command", required=True)
    config = commands.add_parser("validate-config")
    config.add_argument("--mode", choices=["CLEAN", "MESSY"], required=True)
    config.add_argument("--configuration", type=Path, required=True)
    corpus = commands.add_parser("validate-corpus")
    corpus.add_argument("--corpus-root", type=Path, required=True)
    corpus.add_argument("--report", type=Path, required=True)
    example = commands.add_parser(
        "demo",
        help="Build a clean Engine example without a private random-seed override",
    )
    example.add_argument("--private-root", type=Path, required=True)
    example.add_argument("--corpus-root", type=Path, required=True)
    example.add_argument("--credentials", type=Path, required=True)
    example.add_argument("--receipt", type=Path, required=True)
    example.add_argument("--control", default="SH-IAM-007")
    for command in [corpus, example]:
        command.add_argument("--period-start", default="2027-01-04")
        command.add_argument("--period-end", default="2027-12-31")
        command.add_argument("--timezone", default="UTC")
    export = commands.add_parser("export-review")
    export.add_argument("--private-root", type=Path, required=True)
    export.add_argument("--corpus-root", type=Path, required=True)
    export.add_argument("--principal", required=True)
    export.add_argument("--engagement", required=True)
    export.add_argument("--edition", choices=["EVIDENCE", "REVIEWER"], default="EVIDENCE")
    export.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-config":
            normalized = validate_configuration(read_json(args.configuration), args.mode)
            result, failed = (
                {"status": "PASS_CONFIGURATION", "configuration_sha256": digest(normalized)},
                False,
            )
        elif args.command == "validate-corpus":
            result, failed = corpus_check(args)
        elif args.command == "demo":
            result, failed = demo(args)
        else:
            result, failed = export_review(args)
        print(json.dumps(result))
        return int(failed)
    except (DomainError, ValueError, KeyError, TypeError, OSError) as exc:
        # Detailed source/case reports stay in the private output or state.
        print(json.dumps({"status": "FAIL", "code": getattr(exc, "code", type(exc).__name__)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
