"""Fresh, selected-scope SEC003 performance through the ordinary audit engine.

No private Key or historical audit observation is an input. Source grant changes
and collection journals belong only to independent ordinary-byte source copies.
The exact full-scope task stays IN_PROGRESS/LIMITATION pending independent review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .company_federation import QUALIFICATION
from .company_federation import SCHEMA as PORTFOLIO_SCHEMA
from .company_store import CompanyStore, CompanyStoreError, _time
from .documentary_283_route_reconciliation_v5 import P1_RUN
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .engine import Engine
from .fictional_2027_candidate_registry import _private
from .fictional_2027_collection_probe import _ordinary_copy
from .population_lifecycle import population, selection
from .store import canonical, digest

SCHEMA = "SH_FRESH_SEC003_SELECTED_PROCEDURE_V1"
TASK = "TASK-SH-SEC-003-corporate-CHECK-SOC2:CC7.1"
CONTROL = "SH-SEC-003"
COMPANY = "SABLE-HARBOR-REFERENCE"
AS_OF = "2027-12-31T09:00:00+00:00"
OCTOBER = "2027-10-31T23:59:59+00:00"
BASE = "enterprise/generated/audit-suite"
FREEZE = {
    "file_count": 538,
    "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
}
SPEC = "enterprise/audit_suite/sec003_selected_vulnerability_spec_v1.json"
SPEC_SHA = "c4ac9b9de07f046027bb02bdbc4328ef3b49b6f5cba32ad4013280e06e91110d"
PROGRAM_PACK = "enterprise/generated/audit-suite/build/program-pack.json"
PROGRAM_PACK_SHA = "73d856274fbfe65e32a61cffaf3bb101b801e2ff24825be1eddfe8b4f2138134"
SOURCES = {
    "sec003": {
        "folder": "company-sec003-selected-vulnerability-2026-09-30",
        "namespace": "SEC003",
        "prefix": "SEC003-SELECTED-",
        "pins": {
            "MANIFEST.json": "4ae2200e8735ea60e4a85f1158782926fdd50eda96238fc15031d5d9eda69af3",
            "RECEIPT.json": "85233a1e785ffea73f32996bc3f410e9b5c381720b6cbe941ff8a2bbd5474ff8",
            "company.sqlite3": "a94b9f0e2d18e06afd2c83ae2012cea8da72102f9bafcf0e3968959eb6f1539f",
        },
        "review": "f15bc7d94d04fa3599a0f852470e81ea53ce3dc1685d05d0fb15a65901013f36",
    },
    "sec005": {
        "folder": "company-sec005-operated-2026-09-30",
        "namespace": "SEC005",
        "prefix": "SEC005-OPERATED-",
        "pins": {
            "MANIFEST.json": "37b170a7e6688d1bbab4022ff8a239eb3b2e5c44fff76af381a9872c0b84aa32",
            "RECEIPT.json": "157495f5e98d9475f2c88b01954b6e192049183105fe35475350c20885681968",
            "company.sqlite3": "4c258e73de8084b20c65fcad24a96e7f0e3fbb771de431c6e079fc6500d7fd1f",
        },
        "review": "5803081af00997823fa0b0f2a0f40c77effb6cee74bde8d8413f1862b64a90ac",
    },
}
NATIVE_ID = ("company", "branch", "system", "record", "version")
CLOCK_ID = (*NATIVE_ID, "sha256", "event_at", "available_at", "imported_at")


class ProcedureError(ValueError):
    """A source, population, scope or retained workroom failed its exact check."""


def require(condition, message):
    if not condition:
        raise ProcedureError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    data = (
        value
        if isinstance(value, bytes)
        else (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    )
    with path.open("xb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


@contextmanager
def read_only(path):
    db = sqlite3.connect(Path(path).as_uri() + "?mode=ro&immutable=1", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    require(db.execute("PRAGMA quick_check").fetchone()[0] == "ok", "Database integrity differs")
    try:
        yield db
    finally:
        db.close()


def business_digest(path):
    with read_only(path) as db:
        systems = [
            list(row) for row in db.execute("SELECT * FROM systems ORDER BY company,branch,system")
        ]
        versions = []
        for row in db.execute(
            "SELECT * FROM versions ORDER BY company,branch,system,record,version"
        ):
            item = dict(row)
            item["content"] = hashlib.sha256(item["content"]).hexdigest()
            require(item["content"] == item["sha256"], "Native content is damaged")
            versions.append(item)
    return digest([systems, versions])


def discover_history(
    store, principal, engagement, company, branch, *, as_of, systems=None, page_size=2
):
    """Discover records by API, then read every exact immutable version.

    list_records supplies the latest visible version only. Each predecessor is
    therefore explicitly read, and gaps/unavailable predecessors fail closed.
    This is complete only for the granted frozen source and authorized clock.
    """
    visible = store.list_systems(principal, engagement, company, branch)["systems"]
    aliases = sorted(row["system"] for row in visible)
    chosen = aliases if systems is None else sorted(systems)
    require(set(chosen) <= set(aliases), "Discovery system not granted")
    pages, members, seen = [], [], set()
    for system in chosen:
        after = None
        cursors = set()
        while True:
            page = store.list_records(
                principal,
                engagement,
                company,
                branch,
                system,
                as_of=as_of,
                after_record=after,
                limit=page_size,
            )
            latest = page["records"]
            require(all(row["record"] > (after or "") for row in latest), "Discovery cursor failed")
            require(
                [r["record"] for r in latest] == sorted({r["record"] for r in latest}),
                "Duplicate or unordered records",
            )
            pages.append(
                {
                    "system": system,
                    "after_record": after,
                    "limit": page_size,
                    "records": [{k: row[k] for k in CLOCK_ID} for row in latest],
                    "next_after_record": page["next_after_record"],
                }
            )
            for last in latest:
                require(
                    type(last["version"]) is int and 1 <= last["version"] <= 10000,
                    "Version bound differs",
                )
                for number in range(1, last["version"] + 1):
                    try:
                        row = store.read_version(
                            principal,
                            engagement,
                            company,
                            branch,
                            system,
                            last["record"],
                            version=number,
                            as_of=as_of,
                        )
                    except CompanyStoreError as error:
                        raise ProcedureError(
                            "Incomplete visible immutable version history"
                        ) from error
                    key = tuple(row[k] for k in NATIVE_ID)
                    require(
                        key not in seen and row["version"] == number, "Duplicate source version"
                    )
                    require(
                        _time(row["available_at"]) <= _time(as_of)
                        and (row["event_at"] is None or _time(row["event_at"]) <= _time(as_of)),
                        "Future source clock",
                    )
                    require(
                        hashlib.sha256(row["content"]).hexdigest() == row["sha256"],
                        "Source byte hash differs",
                    )
                    if number == last["version"]:
                        require(
                            all(row[k] == last[k] for k in CLOCK_ID),
                            "Discovery/read metadata drift",
                        )
                    seen.add(key)
                    members.append({**row, "discovery_system": system})
            cursor = page["next_after_record"]
            if cursor is None:
                break
            require(
                cursor not in cursors and latest and cursor == latest[-1]["record"],
                "Discovery pagination stalled",
            )
            cursors.add(cursor)
            after = cursor
    current = {
        row["system"]
        for row in store.list_systems(principal, engagement, company, branch)["systems"]
    }
    require(set(chosen) <= current, "Grant revoked during discovery")
    return members, pages


def native_row(artifact, content):
    receipt = artifact["source"]["receipt"]
    return {
        "source": receipt["source"],
        "receipt": receipt,
        "artifact_id": artifact["id"],
        "artifact_sha256": artifact["sha256"],
        "document": json.loads(content),
    }


def analyze(sec, upstream, plan):
    """Reperform observable set/count/chronology joins without branch expectations."""
    records = {r["source"]["record"]: r for r in sec}
    require(len(records) == len(sec), "Pilot requires unambiguous exact native record versions")
    inventory = next(r for r in upstream if r["source"]["system"] == "security_inventory")
    security_baseline = next(r for r in upstream if r["source"]["system"] == "security_baseline")
    expected = sorted(a["id"] for a in inventory["document"]["assets"])
    require(
        expected == sorted(plan["asset_ids"]),
        "Upstream selected inventory differs from declared cohort",
    )
    require(
        sorted(security_baseline["document"]["selected_asset_ids"]) == expected,
        "Upstream baseline inventory differs",
    )
    october = {
        k: r for k, r in records.items() if _time(r["source"]["available_at"]) <= _time(OCTOBER)
    }

    def detail(record):
        return records[record]["document"]["detail"]

    census = set(detail("CENSUS-OCT-01")["observed_asset_ids"])
    baseline = set(detail("BASELINE-OCT-01")["covered_asset_ids"])
    scheduled = set(detail("SCHEDULE-OCT-01")["scheduled_asset_ids"])
    observed = set(detail("SCAN-OCT-01")["observed_asset_ids"])
    advisory = detail(plan["advisory_id"])["advisory"]
    affected = advisory["affected_asset_id"]
    require(
        affected == plan["deep_trace_asset_id"] and affected in expected,
        "Advisory differs from predeclared target",
    )
    finding = set(detail("SCAN-OCT-01")["finding_asset_ids"])
    missing = sorted(set(expected) - observed)
    contradictions = []
    for record, field, ids in (
        ("CENSUS-OCT-01", "observed_count", census),
        ("SCAN-OCT-01", "observed_count", observed),
        ("SCAN-OCT-01", "reported_count", observed),
        ("SCHEDULE-OCT-01", "reported_asset_count", scheduled),
    ):
        claim = detail(record).get(field)
        if claim is not None and claim != len(ids):
            contradictions.append(
                {"record": record, "field": field, "claimed": claim, "recalculated": len(ids)}
            )
    coverage = [
        {
            "asset_id": asset,
            "upstream_inventory": True,
            "upstream_baseline": True,
            "october_census": asset in census,
            "october_baseline": asset in baseline,
            "october_schedule": asset in scheduled,
            "october_scan": asset in observed,
            "october_advisory_finding": asset in finding,
        }
        for asset in expected
    ]
    matching = [r for r in sec if r["document"].get("detail", {}).get("asset_id") == affected]
    triage = [r for r in matching if r["source"]["system"] == "vulnerability_triage"]
    approval = [r for r in matching if r["source"]["system"] == "vulnerability_approval"]
    fixes = [r for r in matching if r["source"]["system"] == "vulnerability_remediation"]
    retests = [
        r
        for r in sec
        if r["source"]["system"] == "vulnerability_scan"
        and r["document"]["action"] == "DATA_ONLY_RETEST"
    ]
    require(
        len(triage) == len(approval) == len(fixes) == len(retests) == 1,
        "Selected deep trace lacks unique native steps",
    )
    detections = [
        r
        for r in sec
        if r["source"]["system"] == "vulnerability_scan"
        and affected in r["document"]["detail"]["finding_asset_ids"]
    ]
    require(len(detections) == 1, "Selected advisory detection needs one exact native scan")
    trace = [
        records[plan["advisory_id"]],
        detections[0],
        triage[0],
        approval[0],
        fixes[0],
        retests[0],
    ]
    chronology = all(
        _time(a["source"]["available_at"]) <= _time(b["source"]["event_at"])
        for a, b in zip(trace, trace[1:], strict=False)
    )
    retest_ids = set(retests[0]["document"]["detail"]["observed_asset_ids"])
    retest_findings = retests[0]["document"]["detail"]["finding_asset_ids"]
    # A source flag asserting false-clean is not an explanation. Inspect native
    # coverage, advisory target and upstream drift/agent-loss records separately.
    missed = affected not in finding
    causal_gap = missed and affected in observed and affected not in missing
    causal = {
        "advisory_asset": affected,
        "omitted_scan_assets": missing,
        "advisory_asset_observed_october": affected in observed,
        "advisory_asset_found_october": affected in finding,
        "omission_explains_missed_advisory": False if causal_gap else None,
        "native_detection_rule_or_parser_version_available": False,
        "disposition": "UNEXPLAINED_FALSE_CLEAN"
        if causal_gap
        else "NO_SELECTED_DETECTION_CONTRADICTION",
        "explanation": (
            "The omitted asset differs from the observed advisory target. "
            "Native baseline marks staleness; "
            "upstream EDGE egress drift and OPS agent loss supply no parser-"
            "version/advisory-rule mechanism. "
            "A causal explanation is unsupported."
            if causal_gap
            else "The selected advisory target has an October finding and a dated correction trace."
        ),
    }
    exceptions = [r for r in sec if r["source"]["system"] == "vulnerability_exception"]
    current = max(
        (r for r in sec if r["source"]["system"] == "vulnerability_reconciliation"),
        key=lambda r: r["source"]["available_at"],
    )
    october_signer = records["RECON-OCT-01"]["document"]["actor_id"]
    later_recon = [
        r
        for r in sec
        if r["source"]["system"] == "vulnerability_reconciliation"
        and _time(r["source"]["event_at"]) > _time(OCTOBER)
    ]
    self_review = any(r["document"]["actor_id"] == october_signer for r in later_recon)
    return {
        "schema": "SH_SEC003_AUDITOR_REPERFORMANCE_V1",
        "selected_expected_assets": expected,
        "asset_census": coverage,
        "source_versions_tested": len(sec),
        "upstream_versions_tested": len(upstream),
        "october_available_record_ids": sorted(october),
        "october_coverage": {
            "census": len(census),
            "baseline": len(baseline),
            "schedule": len(scheduled),
            "scan": len(observed),
            "denominator": len(expected),
            "missing_assets": missing,
        },
        "count_contradictions": contradictions,
        "causal_discrepancy": causal,
        "deep_trace": [
            {
                "record": r["source"]["record"],
                "sha256": r["source"]["sha256"],
                "event_at": r["source"]["event_at"],
                "available_at": r["source"]["available_at"],
            }
            for r in trace
        ],
        "approval_fix_retest_chronology_supported": chronology,
        "current_retest": {
            "asset_ids": sorted(retest_ids),
            "coverage_complete_selected": retest_ids == set(expected),
            "finding_asset_ids": retest_findings,
            "actual_scan_execution": False,
        },
        "exception_dispositions": [
            {"record": r["source"]["record"], "status": r["document"]["detail"]["status"]}
            for r in exceptions
        ],
        "latest_company_reconciliation": {
            "record": current["source"]["record"],
            "detail": current["document"]["detail"],
        },
        "company_self_review_of_october": self_review,
        "company_october_signer": october_signer,
        "conclusion": "LIMITATION",
        "full_enterprise_clause_supported": False,
        "limitations": [
            "Selected four-asset SVC-compute cohort and selected interval "
            "only; full enterprise/year population unestablished.",
            "Native records are authored fictional data-only operations; no "
            "executable scanner, device or real PHI.",
            "A clean selected correction trace cannot establish enterprise CC7.1 effectiveness.",
            "Independent audit reviewer has not accepted this workpaper or selected task scope.",
        ],
    }


def workpaper_text(result, discovery, plan):
    return (
        "SEC003 selected-scope auditor workpaper\n\n"
        "Objective: reconcile upstream inventory, scan census, baseline and schedule by asset ID; "
        "trace one preselected advisory from detection to authorized correction and retest.\n"
        "Scope: four declared SVC-compute assets; native SEC003 "
        "October12–November11,2027 interval, "
        "with separately collected SEC005 foundation and explicitly referenced upstream events. "
        "No enterprise/full-year extrapolation.\n"
        "Selection: a 4/4 census and a judgmental single advisory trace. "
        "The plan was sealed before outcome inspection.\n"
        "Population method: granted CompanyStore list_systems and "
        "paginated list_records, then exact immutable "
        "predecessor reads1..latest; source copies frozen against original"
        " business hashes. Source API clocks "
        "and each retained event/available/imported/collection clock are "
        "preserved separately. Producer receipts "
        "are integrity/locator pins only.\n"
        "October reconstruction uses records available by October31 only. "
        "Later corrections are evaluated separately.\n\n"
        + "Predeclared plan:\n"
        + json.dumps(plan, sort_keys=True, indent=2)
        + "\n\nPopulation query/pagination and exclusions:\n"
        + json.dumps(discovery, sort_keys=True, indent=2)
        + "\n\nAuditor recalculation and bounded observations:\n"
        + json.dumps(result, sort_keys=True, indent=2)
        + "\n\nDisposition: selected-scope procedures performed; exact "
        "authored task remains IN_PROGRESS/LIMITATION, "
        "with no complete task, clause, control, grade, Key or Type2 "
        "opinion credit. Independent review remains pending.\n"
    )


def _command(engine, actor, eid, kind, payload, serial):
    state = engine.store.get(actor, eid)
    return engine.command(
        actor,
        eid,
        {
            "command_id": f"SEC003-{serial}-{kind}",
            "expected_revision": state["revision"],
            "kind": kind,
            "payload": payload,
        },
    )


def _source_pins(repository, private):
    require(sha(repository / SPEC) == SPEC_SHA, "Selected specification differs")
    spec = json.loads((repository / SPEC).read_text())
    require(
        spec["actual_phi"] is False and spec["real_scan_or_deployment"] is False,
        "Synthetic scope differs",
    )
    pins = {str(repository / SPEC): SPEC_SHA}
    _private(private / PROGRAM_PACK)
    require(sha(private / PROGRAM_PACK) == PROGRAM_PACK_SHA, "Frozen program pack differs")
    pins[str(private / PROGRAM_PACK)] = PROGRAM_PACK_SHA
    for source in SOURCES.values():
        root = private / BASE / source["folder"]
        for name, expected in source["pins"].items():
            path = root / "main-run-v1" / name
            _private(path)
            require(sha(path) == expected, "Source package hash differs: " + name)
            pins[str(path)] = expected
        review = root / "independent-review-main-v1/REVIEW.json"
        _private(review)
        require(sha(review) == source["review"], "Source independent review pin differs")
        pins[str(review)] = source["review"]
    return spec, pins


def _baseline(private, side):
    path = private / BASE / P1_RUN / "audit" / side / "audit-state/engagements.sqlite3"
    with read_only(path) as db:
        rows = db.execute("SELECT state FROM engagements").fetchall()
    require(len(rows) == 1, "Frozen baseline engagement count differs")
    baseline = json.loads(rows[0][0])
    require(
        len(baseline["tasks"]) == 409
        and all(
            t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN" for t in baseline["tasks"]
        ),
        "Frozen baseline task state differs",
    )
    return baseline


def _upstream_refs(sec):
    refs = {}
    for row in sec:
        for ref in row["document"]["upstream_native_refs_available_at_event"].values():
            key = tuple(ref[k] for k in NATIVE_ID)
            require(
                _time(ref["available_at"]) <= _time(row["source"]["event_at"]),
                "Future upstream business join",
            )
            if key in refs:
                require(
                    all(ref[k] == refs[key][k] for k in CLOCK_ID), "Contradictory upstream locator"
                )
            refs[key] = ref
    return refs


def validate_native_chain(sec):
    """Join immutable earlier SEC003 originals, including their three clocks."""
    indexed = {(r["source"]["system"], r["source"]["record"]): r for r in sec}
    require(len(indexed) == len(sec), "Native source sequence duplicates a record")
    for row in sec:
        document, source = row["document"], row["source"]
        require(
            all(
                document[k] == source[k]
                for k in ("company", "system", "record", "event_at", "available_at")
            ),
            "Native document clocks/identity differ from stored source",
        )
        previous = document["source_previous"]
        if previous is None:
            continue
        predecessor = indexed.get((previous["system"], previous["record"]))
        require(
            predecessor is not None
            and all(
                predecessor["source"][k] == previous[k]
                for k in ("system", "record", "sha256", "event_at", "available_at")
            ),
            "Native immutable predecessor join differs",
        )
        require(
            _time(previous["available_at"]) <= _time(source["event_at"]),
            "Native predecessor was future to event",
        )


def run(repository, private_repository, destination):
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    destination = Path(destination).absolute()
    require(not destination.exists() and not destination.is_symlink(), "Fresh destination required")
    _private(destination.parent, directory=True)
    require(_p1_inventory(private) == FREEZE, "Frozen P1 inventory differs")
    spec, pins = _source_pins(repository, private)
    destination.mkdir(mode=0o700)
    write(destination / "IMPLEMENTATION.py", Path(__file__).read_bytes())
    report = {
        "schema": SCHEMA,
        "implementation_sha256": sha(destination / "IMPLEMENTATION.py"),
        "repository": str(repository),
        "private_repository": str(private),
        "p1_before": FREEZE,
        "source_pins": pins,
        "branches": {},
        "bounded_procedure_performed": True,
        "audit_task_credit": False,
        "independent_review": "NOT_PERFORMED",
        "key_or_historical_evidence_used": False,
    }
    for side, mode in (("A", "CLEAN"), ("B", "MESSY")):
        root = destination / side
        root.mkdir(mode=0o700)
        components, copies = {}, {}
        for key, source in SOURCES.items():
            origin = private / BASE / source["folder"] / "main-run-v1/company.sqlite3"
            copy = root / key / "company.sqlite3"
            _ordinary_copy(origin, copy)
            with read_only(copy) as db:
                require(
                    all(
                        db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0
                        for t in ("grants", "collections", "access_events")
                    ),
                    "Inherited source access journal",
                )
                systems = [
                    r[0]
                    for r in db.execute(
                        "SELECT system FROM systems WHERE company=? AND branch=? ORDER BY system",
                        (COMPANY, source["prefix"] + mode),
                    )
                ]
            components[key] = {
                "root": str(copy.parent),
                "company": COMPANY,
                "branch": source["prefix"] + mode,
                "namespace": source["namespace"],
                "systems": systems,
            }
            copies[key] = {
                "origin": str(origin),
                "copy": str(copy),
                "initial_sha256": sha(copy),
                "business_sha256": business_digest(copy),
            }
        profile = "FRESH-SEC003-" + side
        registry = {
            "schema": PORTFOLIO_SCHEMA,
            "components": components,
            "profiles": {
                profile: {
                    "company": COMPANY,
                    "components": sorted(components),
                    "qualification": QUALIFICATION,
                }
            },
        }
        write(root / "REGISTRY.json", registry)
        _ordinary_copy(private / PROGRAM_PACK, root / "program-pack.json")
        engine = Engine(
            root / "audit-state",
            repository=repository,
            program_pack=root / "program-pack.json",
            company_registry=root / "REGISTRY.json",
            company_profile=profile,
        )
        operator = engine.store.provision("Fresh SEC003 source operator " + side, ["instructor"])[
            "id"
        ]
        auditor = engine.store.provision("Fresh SEC003 audit performer " + side, ["learner"])["id"]
        reviewer = engine.store.provision(
            "Reserved independent SEC003 reviewer " + side, ["reviewer"]
        )["id"]
        require(len({operator, auditor, reviewer}) == 3, "Distinct identities required")
        baseline = _baseline(private, side)
        state = engine.create(
            operator,
            {
                "command_id": "fresh-sec003-create",
                "title": "Fresh selected SEC003 " + side,
                "discipline": baseline["discipline"],
                "mode": mode,
                "scope": baseline["scope"],
                "configuration": {"selections": []},
            },
        )
        eid = state["id"]
        frozen_task = next(t for t in baseline["tasks"] if t["id"] == TASK)
        fresh_task = next(t for t in state["tasks"] if t["id"] == TASK)
        require(
            all(
                fresh_task[k] == frozen_task[k]
                for k in (
                    "id",
                    "test",
                    "title",
                    "control_id",
                    "kind",
                    "requirement_ids",
                    "owner_id",
                )
            ),
            "Fresh task differs from frozen exact procedure",
        )
        require(
            len(state["tasks"]) == 409
            and all(
                t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
                for t in state["tasks"]
            ),
            "Fresh task baseline differs",
        )
        empty = {
            k: len(state[k])
            for k in (
                "artifacts",
                "workpapers",
                "populations",
                "selections",
                "reviews",
                "findings",
                "requests",
            )
        }
        require(not any(empty.values()), "New engagement inherited audit work")
        engine.store.grant(eid, auditor, "learn")
        engine.store.grant(eid, reviewer, "review")
        engine.company_bindings[eid] = dict(engine.company_store.binding)
        write(
            root / "START.json",
            {
                "engagement_id": eid,
                "zero_workroom_counts": empty,
                "task_count": len(state["tasks"]),
                "creation": "Engine.create from scope/configuration; no mutable baseline "
                "collections copied",
                "operator_id": operator,
                "auditor_id": auditor,
                "reviewer_id": reviewer,
            },
        )
        state = _command(engine, operator, eid, "company.activate", {}, "activate")
        state = _command(engine, auditor, eid, "kickoff.start", {}, "kickoff")
        plan = {
            "task_id": TASK,
            "task_digest_before_performance": digest(fresh_task),
            "asset_ids": spec["selected_asset_ids"],
            "service_id": spec["service_id"],
            "sec003_event_interval": spec["selected_period"],
            "authorized_source_clock": AS_OF,
            "advisory_id": spec["synthetic_advisory"]["id"],
            "deep_trace_asset_id": spec["synthetic_advisory"]["affected_asset_id"],
            "additional_coverage_challenge_asset_id": "SIM-BOI-OPS-01",
            "census_method": "ENTIRE_SELECTED_COHORT",
            "deep_trace_method": "JUDGMENTAL_PREDECLARED_ADVISORY",
            "basis": "Predeclared selected scope and advisory; no outcome, historical "
            "evidence or Key input",
            "selection_sealed_at": datetime.now(UTC).isoformat(),
            "performer_id": auditor,
            "scope_acceptance": "SELECTED_PILOT_ONLY_PENDING_INDEPENDENT_TASK_SCOPE_REVIEW",
        }
        write(root / "PLAN.json", plan)
        state = _command(
            engine,
            auditor,
            eid,
            "task.update",
            {
                "task_id": TASK,
                "status": "IN_PROGRESS",
                "note": "Selected-scope native-source procedure in progress; full task not"
                " credited.",
            },
            "begin",
        )
        state = _command(
            engine,
            auditor,
            eid,
            "pbc.create",
            {
                "title": "SEC003 selected native history and SEC005 joins",
                "purpose": "Direct source inspection and exact selected-version collection "
                "for declared four-asset procedure",
                "control_id": CONTROL,
                "person_id": "AS-P008",
                "boundary_id": "corporate",
            },
            "pbc",
        )
        request = state["requests"][-1]["id"]
        state = _command(engine, auditor, eid, "pbc.issue", {"request_id": request}, "issue")
        access = []

        def grant(
            key,
            systems,
            active,
            components=components,
            auditor=auditor,
            eid=eid,
            access=access,
            operator=operator,
        ):
            component = components[key]
            store = CompanyStore(Path(component["root"]))
            for system in sorted(systems):
                store.grant(auditor, eid, COMPANY, component["branch"], system, active=active)
                access.append(
                    {
                        "operator_id": operator,
                        "principal_id": auditor,
                        "engagement_id": eid,
                        "component": key,
                        "branch": component["branch"],
                        "system": system,
                        "active": active,
                    }
                )

        grant("sec003", components["sec003"]["systems"], True)
        discovered, pages = discover_history(
            engine.company_store,
            auditor,
            eid,
            COMPANY,
            profile,
            as_of=AS_OF,
            systems=["SEC003:" + s for s in components["sec003"]["systems"]],
        )
        selected = [
            r
            for r in discovered
            if _time(spec["selected_period"][0])
            <= _time(r["event_at"])
            <= _time(spec["selected_period"][1])
        ]
        excluded = [{k: r[k] for k in CLOCK_ID} for r in discovered if r not in selected]
        require(
            len(selected) == (11 if side == "A" else 18), "Selected native sequence count differs"
        )
        collected = []

        def collect(
            rows,
            label,
            engine=engine,
            auditor=auditor,
            eid=eid,
            request=request,
            collected=collected,
        ):
            result = []
            for index, row in enumerate(rows):
                state = _command(
                    engine,
                    auditor,
                    eid,
                    "company.collect",
                    {
                        "system_id": row["discovery_system"],
                        "record_id": row["record"],
                        "version": row["version"],
                        "request_id": request,
                    },
                    label + str(index),
                )
                artifact = state["artifacts"][-1]
                require(
                    all(artifact["source"]["receipt"]["source"][k] == row[k] for k in CLOCK_ID),
                    "Collected source identity differs",
                )
                require(
                    engine.artifacts.read(artifact) == row["content"],
                    "Retained bytes differ from exact native version",
                )
                item = native_row(artifact, row["content"])
                result.append(item)
                collected.append(item)
            return result

        sec = collect(selected, "sec003")
        validate_native_chain(sec)
        refs = _upstream_refs(sec)
        upstream_systems = sorted({r["system"] for r in refs.values()})
        require(
            set(upstream_systems) <= set(components["sec005"]["systems"]),
            "Unexpected upstream system",
        )
        grant("sec005", upstream_systems, True)
        upstream_discovered, upstream_pages = discover_history(
            engine.company_store,
            auditor,
            eid,
            COMPANY,
            profile,
            as_of=AS_OF,
            systems=["SEC005:" + s for s in upstream_systems],
        )
        indexed = {tuple(r[k] for k in NATIVE_ID): r for r in upstream_discovered}
        require(
            set(refs) <= set(indexed), "Required upstream originals absent from native discovery"
        )
        for key, ref in refs.items():
            require(
                all(indexed[key][k] == ref[k] for k in CLOCK_ID),
                "Exact upstream clocks/content do not join",
            )
        upstream = collect([indexed[k] for k in sorted(refs)], "sec005")
        grant("sec003", components["sec003"]["systems"], False)
        grant("sec005", upstream_systems, False)
        require(
            not engine.company_store.list_systems(auditor, eid, COMPANY, profile)["systems"],
            "Source grant still active",
        )
        try:
            engine.company_store.read_version(
                auditor,
                eid,
                COMPANY,
                profile,
                selected[0]["discovery_system"],
                selected[0]["record"],
                version=selected[0]["version"],
                as_of=AS_OF,
            )
        except CompanyStoreError:
            pass
        else:
            raise ProcedureError("Revoked source remained readable")
        discovery = {
            "api": "list_systems/list_records/exact read_version/collect",
            "page_size": 2,
            "history_basis": "All contiguous immutable versions1..latest directly read; any gap"
            " fails incomplete",
            "source_freeze": copies,
            "snapshot_isolation": "Frozen ordinary copies; no global live transaction asserted",
            "sec003_pages": pages,
            "sec005_pages": upstream_pages,
            "sec003_observed_versions": len(selected),
            "sec003_excluded_versions": excluded,
            "sec005_collected_exact_joins": [
                {k: r["source"][k] for k in CLOCK_ID} for r in upstream
            ],
            "sec005_excluded_unreferenced_versions": [
                {k: r[k] for k in CLOCK_ID} for k, r in indexed.items() if k not in refs
            ],
            "exclusion_reason": "Upstream systems only for exact SEC003 cited joins; other SEC005 "
            "activity outside this selected procedure",
        }
        result = analyze(sec, upstream, plan)
        text = workpaper_text(result, discovery, plan)
        write(root / "COLLECTION.json", collected)
        write(root / "DISCOVERY.json", discovery)
        write(root / "ACCESS.json", access)
        write(root / "REPERFORMANCE.json", result)
        write(root / "WORKPAPER.txt", text.encode())
        inventory = next(r for r in upstream if r["source"]["system"] == "security_inventory")
        state = _command(
            engine,
            auditor,
            eid,
            "population.import",
            {
                "artifact_id": inventory["artifact_id"],
                "title": "SEC003 selected four-asset upstream census",
                "rows": [{"id": a} for a in result["selected_expected_assets"]],
                "scope": {
                    "boundary_id": "corporate",
                    "unit": "SVC-compute",
                    "timezone": "UTC",
                    "period_start": spec["selected_period"][0],
                    "period_end": spec["selected_period"][1],
                },
                "source": {
                    "source_id": "SEC005:security_inventory/INVENTORY-SELECTED-01",
                    "query": "Exact native $.assets[*].id joined to SEC005 baseline and SEC003 "
                    "native discovered selected history",
                    "completeness_representation": (
                        "Selected four-asset inventory only; full enterprise/year unknown"
                    ),
                    "excluded_ids": [],
                },
            },
            "population",
        )
        popid = state["populations"][-1]["id"]
        state = _command(
            engine,
            auditor,
            eid,
            "population.assess",
            {
                "population_id": popid,
                "status": "READY_FOR_PURPOSE",
                "purpose": "Selected four-asset census; no broader population reliability",
                "rationale": "Auditor reconciled exact SEC005 inventory/baseline IDs and all "
                "selected native SEC003 versions. Independent review pending.",
                "observable_artifact_ids": [r["artifact_id"] for r in upstream],
            },
            "assess",
        )
        poprow = state["populations"][-1]
        state = _command(
            engine,
            auditor,
            eid,
            "population.select",
            {
                "population_id": poprow["id"],
                "method": "ENTIRE",
                "purpose": "4/4 selected asset census",
                "rationale": "Predeclared full selected cohort; no statistical extrapolation",
            },
            "census",
        )
        census_selection = state["selections"][-1]
        state = _command(
            engine,
            auditor,
            eid,
            "population.select",
            {
                "population_id": poprow["id"],
                "method": "MANUAL",
                "selected_ids": [plan["deep_trace_asset_id"]],
                "purpose": "One predeclared advisory correction trace",
                "rationale": "Judgmental disclosed advisory target sealed before outcome "
                "inspection",
            },
            "deep",
        )
        deep_selection = state["selections"][-1]
        require(len(text) <= 200000, "Workpaper too large")
        state = _command(
            engine,
            auditor,
            eid,
            "workpaper.add",
            {
                "title": "SEC003 selected native census and advisory trace",
                "control_id": CONTROL,
                "task_ids": [TASK],
                "text": text,
                "objective": "Selected inventory/scan/baseline and advisory reconciliation",
                "procedures": "Direct discovery and collection; asset-ID census, dated October "
                "reconstruction, approval/fix/retest trace and exception challenge",
                "evidence_ids": [r["artifact_id"] for r in collected],
                "conclusion": "LIMITATION",
            },
            "workpaper",
        )
        paper = state["workpapers"][-1]
        census_evidence = [
            r
            for r in collected
            if r in upstream
            or r["source"]["record"]
            in {
                "CENSUS-OCT-01",
                "BASELINE-OCT-01",
                "SCHEDULE-OCT-01",
                "SCAN-OCT-01",
                "RECON-OCT-01",
            }
        ]
        deep_evidence = [
            r
            for r in collected
            if (
                r in upstream
                and r["source"]["system"] not in {"security_inventory", "security_baseline"}
            )
            or (
                r not in upstream
                and r["source"]["system"]
                not in {"vulnerability_inventory", "vulnerability_schedule"}
            )
        ]
        require(
            len(census_evidence) <= 20 and len(deep_evidence) <= 20,
            "Evidence trace exceeds engine item bound",
        )

        def refs_for(rows):
            return [
                {
                    "artifact_id": r["artifact_id"],
                    "sha256": r["artifact_sha256"],
                    "locator": "Exact native JSON "
                    + r["source"]["system"]
                    + "/"
                    + r["source"]["record"]
                    + " $.detail/$.assets; custody in source receipt",
                }
                for r in rows
            ]

        for label, chosen, items in (
            (
                "census",
                census_selection,
                [
                    {
                        "item_id": r["asset_id"],
                        "observation": json.dumps(r, sort_keys=True),
                        "status": "OBSERVED"
                        if all(
                            r[k]
                            for k in (
                                "october_census",
                                "october_baseline",
                                "october_schedule",
                                "october_scan",
                            )
                        )
                        else "EXCEPTION_RECORDED",
                        "evidence": refs_for(census_evidence),
                    }
                    for r in result["asset_census"]
                ],
            ),
            (
                "deep",
                deep_selection,
                [
                    {
                        "item_id": plan["deep_trace_asset_id"],
                        "observation": json.dumps(
                            {
                                "causal_discrepancy": result["causal_discrepancy"],
                                "trace": result["deep_trace"],
                                "retest": result["current_retest"],
                                "chronology": result["approval_fix_retest_chronology_supported"],
                            },
                            sort_keys=True,
                        ),
                        "status": "EXCEPTION_RECORDED"
                        if result["causal_discrepancy"]["disposition"] == "UNEXPLAINED_FALSE_CLEAN"
                        else "OBSERVED",
                        "evidence": refs_for(deep_evidence),
                    }
                ],
            ),
        ):
            state = _command(
                engine,
                auditor,
                eid,
                "sample.execution.record",
                {
                    "task_id": TASK,
                    "task_digest": digest(next(t for t in state["tasks"] if t["id"] == TASK)),
                    "population_id": poprow["id"],
                    "population_digest": population(poprow).sha256,
                    "selection_id": chosen["id"],
                    "selection_digest": selection(chosen).sha256,
                    "workpaper_id": paper["id"],
                    "workpaper_version": 1,
                    "workpaper_digest": digest(paper["versions"][0]),
                    "purpose": "Selected-scope " + label,
                    "procedure": "Reperformance recorded in exact linked auditor-authored "
                    "workpaper; limited selected scope",
                    "items": items,
                },
                "trace-" + label,
            )
        findings = [
            (
                "Full authored clause population unestablished",
                "Selected four-asset interval has been performed; enterprise/year "
                "inventory, scans and baseline populations remain unestablished.",
                "SCOPE_LIMITATION",
            )
        ]
        if result["october_coverage"]["missing_assets"] or result["count_contradictions"]:
            findings.append(
                (
                    "Selected October coverage and reported count disagree",
                    json.dumps(
                        {
                            "coverage": result["october_coverage"],
                            "contradictions": result["count_contradictions"],
                        },
                        sort_keys=True,
                    ),
                    "SELECTED_OPERATING_EXCEPTION",
                )
            )
        if result["causal_discrepancy"]["disposition"] == "UNEXPLAINED_FALSE_CLEAN":
            findings.append(
                (
                    "Observed advisory target missed without native causal explanation",
                    json.dumps(result["causal_discrepancy"], sort_keys=True),
                    "UNRESOLVED_CAUSAL_DISCREPANCY",
                )
            )
        if result["company_self_review_of_october"]:
            findings.append(
                (
                    "Company November review repeats October signer",
                    "Native AS-P008 November reconciliation reviews AS-P008 October "
                    "sign-off; current retest does not close the open historical "
                    "exception or establish independent company review.",
                    "SELF_REVIEW_LIMITATION",
                )
            )
        for index, (title, condition, classification) in enumerate(findings):
            state = _command(
                engine,
                auditor,
                eid,
                "finding.create",
                {
                    "title": title,
                    "condition": condition,
                    "classification": classification,
                    "control_id": CONTROL,
                    "criterion": "Exact SEC003/CC7.1 authored procedure and declared selected "
                    "source scope",
                    "evidence_ids": [r["artifact_id"] for r in collected],
                },
                "finding" + str(index),
            )
        state = _command(
            engine,
            auditor,
            eid,
            "task.update",
            {
                "task_id": TASK,
                "status": "IN_PROGRESS",
                "conclusion": "LIMITATION",
                "rationale": "Selected native census and advisory trace performed; full "
                "enterprise/year clause population, independent review and task-"
                "scope acceptance remain pending. No full task credit.",
            },
            "limited",
        )
        require(
            all(
                t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
                for t in state["tasks"]
                if t["id"] != TASK
            ),
            "Unrelated task promoted",
        )
        require(not state["reviews"], "Performer manufactured independent review")
        for copy in copies.values():
            require(
                business_digest(copy["copy"]) == copy["business_sha256"],
                "Native source history changed during audit",
            )
            require(
                sha(copy["origin"]) == copy["initial_sha256"],
                "Original source changed during audit",
            )
        report["branches"][side] = {
            "engagement_id": eid,
            "operator_id": operator,
            "auditor_id": auditor,
            "reviewer_id": reviewer,
            "zero_workroom_counts": empty,
            "sec003_versions_collected": len(sec),
            "sec005_versions_collected": len(upstream),
            "workpaper_id": paper["id"],
            "workpaper_version_sha256": digest(paper["versions"][0]),
            "sample_execution_count": len(state["sample_executions"]),
            "finding_count": len(state["findings"]),
            "task_count": len(state["tasks"]),
            "exact_task_status": "IN_PROGRESS",
            "exact_task_conclusion": "LIMITATION",
            "complete_task_count": sum(t["status"] == "COMPLETE" for t in state["tasks"]),
            "audit_task_credit": False,
            "company_source_grants_revoked": True,
            "workpaper_file_sha256": sha(root / "WORKPAPER.txt"),
            "reperformance_sha256": sha(root / "REPERFORMANCE.json"),
        }
        write(root / "FINAL_STATE.json", engine.store.get(auditor, eid))
        with engine.store.connect() as db:
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    require(_p1_inventory(private) == FREEZE, "Frozen P1 inventory changed")
    require(
        all(sha(path) == expected for path, expected in pins.items()),
        "Original source inputs changed",
    )
    report["p1_after"] = FREEZE
    write(destination / "REPORT.json", report)
    files = []
    for path in sorted(destination.rglob("*")):
        if path.is_dir():
            path.chmod(0o700)
        elif path.is_file():
            path.chmod(0o600)
            require(
                not path.is_symlink() and path.stat().st_nlink == 1, "Private output file alias"
            )
            files.append(
                {
                    "path": path.relative_to(destination).as_posix(),
                    "sha256": sha(path),
                    "bytes": path.stat().st_size,
                }
            )
    write(
        destination / "MANIFEST.json",
        {"schema": SCHEMA + "_MANIFEST", "files": files, "file_inventory_sha256": digest(files)},
    )
    return report


def verify_audit_journal(path, final, start):
    """Reperform the actual command chain, membership, and zero-evidence start."""
    with read_only(path) as db:
        stored = db.execute(
            "SELECT state,revision FROM engagements WHERE id=?", (final["id"],)
        ).fetchone()
        require(
            stored is not None
            and json.loads(stored[0]) == final
            and stored[1] == final["revision"],
            "Actual engine state differs from retained final state",
        )
        memberships = dict(
            db.execute(
                "SELECT principal,permission FROM members WHERE engagement=?", (final["id"],)
            )
        )
        require(
            memberships
            == {
                start["operator_id"]: "instruct",
                start["auditor_id"]: "learn",
                start["reviewer_id"]: "review",
            },
            "Auditor/reviewer membership separation differs",
        )
        rows = db.execute(
            "SELECT * FROM events WHERE engagement=? ORDER BY revision", (final["id"],)
        ).fetchall()
    require(len(rows) == final["revision"] + 1, "Engine command revision sequence differs")
    previous = ""
    for number, event in enumerate(rows):
        state = json.loads(event["state"])
        command = json.loads(event["command"])
        require(
            event["revision"] == number
            and state["revision"] == number
            and event["previous_hash"] == previous,
            "Audit engine journal revision/hash linkage differs",
        )
        require(event["request_hash"] == digest(command), "Audit engine command hash differs")
        envelope = {
            "actor": event["actor"],
            "recorded_at": event["recorded_at"],
            "previous_hash": previous,
            "state": state,
            "command": command,
            "command_id": event["command_id"],
        }
        require(digest(envelope) == event["hash"], "Audit engine event hash differs")
        if number == 0:
            require(
                command["kind"] == "engagement.create"
                and event["actor"] == start["operator_id"]
                and not any(state[k] for k in start["zero_workroom_counts"]),
                "Audit did not start without evidence",
            )
            require(
                all(
                    t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
                    for t in state["tasks"]
                ),
                "Audit initial tasks inherited results",
            )
        elif command["kind"] == "company.activate":
            require(event["actor"] == start["operator_id"], "Source activation actor differs")
        else:
            require(event["actor"] == start["auditor_id"], "Procedure command actor differs")
        previous = event["hash"]
    require(
        all(
            p["prepared_by"] == start["auditor_id"]
            and all(v["actor"] == start["auditor_id"] for v in p["versions"])
            for p in final["workpapers"]
        ),
        "Workpaper performer differs",
    )


def verify(destination):
    """Read-only exact output/custody/source and arithmetic verification."""
    destination = Path(destination).resolve(strict=True)
    _private(destination, directory=True)
    manifest = json.loads((destination / "MANIFEST.json").read_text())
    require(
        manifest["schema"] == SCHEMA + "_MANIFEST"
        and digest(manifest["files"]) == manifest["file_inventory_sha256"],
        "Manifest differs",
    )
    expected_paths = {entry["path"] for entry in manifest["files"]}
    actual_paths = {
        p.relative_to(destination).as_posix()
        for p in destination.rglob("*")
        if p.is_file() and p.name != "MANIFEST.json"
    }
    require(actual_paths == expected_paths, "Output inventory differs")
    for entry in manifest["files"]:
        path = destination / entry["path"]
        _private(path)
        require(
            sha(path) == entry["sha256"] and path.stat().st_size == entry["bytes"],
            "Output file hash differs",
        )
    report = json.loads((destination / "REPORT.json").read_text())
    require(
        sha(destination / "IMPLEMENTATION.py") == report["implementation_sha256"],
        "Implementation pin differs",
    )
    require(
        report["audit_task_credit"] is False and report["independent_review"] == "NOT_PERFORMED",
        "Credit boundary differs",
    )
    require(
        _p1_inventory(Path(report["private_repository"])) == FREEZE, "Frozen P1 inventory differs"
    )
    require(
        all(sha(path) == expected for path, expected in report["source_pins"].items()),
        "Original source pin differs",
    )
    counts = {}
    for side in "AB":
        root = destination / side
        final = json.loads((root / "FINAL_STATE.json").read_text())
        start = json.loads((root / "START.json").read_text())
        verify_audit_journal(root / "audit-state/engagements.sqlite3", final, start)
        collected = json.loads((root / "COLLECTION.json").read_text())
        plan = json.loads((root / "PLAN.json").read_text())
        discovery = json.loads((root / "DISCOVERY.json").read_text())
        result = json.loads((root / "REPERFORMANCE.json").read_text())
        require(
            not any(start["zero_workroom_counts"].values())
            and len(set(start[k] for k in ("operator_id", "auditor_id", "reviewer_id"))) == 3,
            "Fresh/separate identities differ",
        )
        require(
            final["id"] == start["engagement_id"] == report["branches"][side]["engagement_id"],
            "Engagement identity differs",
        )
        sec = [r for r in collected if r["source"]["system"].startswith("vulnerability_")]
        upstream = [r for r in collected if r not in sec]
        validate_native_chain(sec)
        require(
            len(sec) == (11 if side == "A" else 18) and len(upstream) == (2 if side == "A" else 7),
            "Collected counts differ",
        )
        require(analyze(sec, upstream, plan) == result, "Auditor arithmetic differs")
        require(
            workpaper_text(result, discovery, plan).encode()
            == (root / "WORKPAPER.txt").read_bytes(),
            "Auditor workpaper differs",
        )
        artifacts = {a["id"]: a for a in final["artifacts"]}
        for item in collected:
            source = item["source"]
            key = "sec003" if source["system"].startswith("vulnerability_") else "sec005"
            require(
                source["company"] == COMPANY
                and source["branch"]
                == SOURCES[key]["prefix"] + ("CLEAN" if side == "A" else "MESSY"),
                "Collected source crossed declared company/branch",
            )
            require(
                _time(item["receipt"]["collected_at"]) >= _time(source["imported_at"]),
                "Actual collection precedes import",
            )
            require(
                _time(plan["selection_sealed_at"]) <= _time(item["receipt"]["collected_at"]),
                "Sample plan postdates collection",
            )
            with read_only(root / key / "company.sqlite3") as db:
                native = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    tuple(source[k] for k in NATIVE_ID),
                ).fetchone()
                require(
                    native is not None and all(native[k] == source[k] for k in CLOCK_ID),
                    "Native custody identity differs",
                )
                require(
                    json.loads(native["content"]) == item["document"],
                    "Collected observation differs from original",
                )
                journal = db.execute(
                    "SELECT receipt FROM collections WHERE command_id=?",
                    (item["receipt"]["upstream_receipt"]["command_id"],),
                ).fetchone()
                require(
                    journal and json.loads(journal[0]) == item["receipt"]["upstream_receipt"],
                    "Collection custody journal differs",
                )
            artifact = artifacts[item["artifact_id"]]
            require(
                artifact["source"]["receipt"] == item["receipt"]
                and artifact["sha256"] == source["sha256"],
                "Retained audit receipt differs",
            )
            # Native Artifacts storage is addressed by exact content hash.
            artifact_path = root / "audit-state" / "artifacts" / artifact["sha256"]
            require(sha(artifact_path) == source["sha256"], "Retained exact content hash differs")
            require(
                item["receipt"]["principal_id"] == start["auditor_id"]
                and item["receipt"]["engagement_id"] == final["id"],
                "Collection actor differs",
            )
        for key, entry in discovery["source_freeze"].items():
            require(
                business_digest(root / key / "company.sqlite3") == entry["business_sha256"],
                "Copied company business history differs",
            )
            with read_only(root / key / "company.sqlite3") as db:
                require(
                    db.execute("SELECT COUNT(*) FROM grants WHERE active=1").fetchone()[0] == 0,
                    "Grant still active",
                )
        task = next(t for t in final["tasks"] if t["id"] == TASK)
        require(
            task["status"] == "IN_PROGRESS"
            and task["conclusion"] == "LIMITATION"
            and len(final["tasks"]) == 409,
            "Exact task disposition differs",
        )
        require(
            all(
                t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
                for t in final["tasks"]
                if t["id"] != TASK
            ),
            "Unrelated task credit changed",
        )
        require(
            not final["reviews"]
            and len(final["workpapers"]) == 1
            and len(final["sample_executions"]) == 2,
            "Workpaper/review trace differs",
        )
        counts[side] = {
            "sec003": len(sec),
            "sec005": len(upstream),
            "sample_traces": 2,
            "credited_tasks": 0,
        }
    return {
        "schema": SCHEMA + "_VERIFY",
        "status": "VERIFIED_SELECTED_PERFORMANCE_PENDING_INDEPENDENT_REVIEW",
        "manifest_sha256": sha(destination / "MANIFEST.json"),
        "report_sha256": sha(destination / "REPORT.json"),
        "p1_unchanged": True,
        "branches": counts,
        "audit_task_credit": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--repository", required=True, type=Path)
    run_parser.add_argument("--private-repository", required=True, type=Path)
    run_parser.add_argument("--destination", required=True, type=Path)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    if args.action == "run":
        result = run(args.repository, args.private_repository, args.destination)
    else:
        result = verify(args.destination)
    print(canonical(result))


if __name__ == "__main__":
    main()
