"""Causal matter gates and independently repeatable client-owned handovers.

The business v1 pricing engine remains responsible for all fee calculations.
These synthetic case files determine whether that engine may act on a matter.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from enterprise.business.advisory import check_matter, check_transfer
from enterprise.business.model import period

CLASSIFICATION = "PUBLIC_SYNTHETIC_CONDITIONAL_FORECAST"
TABLES = (
    "matter_determinations",
    "matter_controls",
    "matter_gate_decisions",
    "matter_handover_evidence",
)
DECISIONS = {
    "ACCEPT": ("acceptance_principal", "acceptance", "PASS"),
    "RIGHTS_MISSING": ("acceptance_principal", "rights", "FAIL"),
    "RIGHTS_CLEARED": ("acceptance_principal", "rights", "PASS"),
    "REVIEW_FAILED": ("independent_reviewer", "review", "FAIL"),
    "REVIEW_CORRECTED": ("independent_reviewer", "review", "PASS"),
    "STOP": ("matter_principal", "stop", "FAIL"),
    "RESUME": ("acceptance_principal", "stop", "PASS"),
    "MATERIAL_CHANGE": ("matter_principal", "scope", "FAIL"),
    "REACCEPT": ("acceptance_principal", "scope", "PASS"),
    "DECLINE": ("acceptance_principal", "acceptance", "DECLINED"),
}
CONTROLS = (
    "acceptance",
    "scope",
    "competence",
    "conflicts",
    "rights",
    "economics",
    "review",
    "stop",
)


def _inputs(model):
    supplied = getattr(model, "operations_inputs", {}).get("matters")
    return (
        supplied
        if supplied is not None
        else json.loads(Path(__file__).with_name("source").joinpath("matters.json").read_text())
    )


def _source_check(model):
    inputs = _inputs(model)
    if inputs["classification"] != CLASSIFICATION:
        raise ValueError("Matter histories must remain explicitly synthetic")
    engagements = {e["engagement_id"]: e for e in model.inputs["engagements"]}
    seen = set()
    for case in inputs["matters"]:
        eid = case["engagement_id"]
        if eid in seen or eid not in engagements or engagements[eid]["unit"] != "advisory":
            raise ValueError("Matter history must identify one existing Advisory matter")
        seen.add(eid)
        e = engagements[eid]
        check_matter(e)
        prior = 0
        states = {name: "PASS" for name in CONTROLS}
        states["acceptance"] = "PENDING"
        for entry in case["events"]:
            month, decision = entry["month"], entry["decision"]
            if type(month) is not int or not e["start_month"] <= month <= 60 or month <= prior:
                raise ValueError("Matter decisions must be distinct chronological forecast months")
            if decision not in DECISIONS or not entry["reason"]:
                raise ValueError("Unknown or unexplained matter decision")
            role, control, result = DECISIONS[decision]
            if entry["role"] != role:
                raise ValueError("Matter decision lacks required independent authority")
            if states["acceptance"] == "DECLINED":
                raise ValueError("A declined matter cannot be reopened under its original identity")
            if (
                decision in {"REVIEW_CORRECTED", "RESUME", "REACCEPT", "RIGHTS_CLEARED"}
                and states[control] != "FAIL"
            ):
                raise ValueError("Matter correction must follow its corresponding failed gate")
            if decision == "ACCEPT" and states["acceptance"] != "PENDING":
                raise ValueError("Duplicate initial acceptance")
            states[control] = result
            if decision == "RIGHTS_CLEARED":
                states["acceptance"] = "PASS"
            prior = month
        if not case["events"]:
            raise ValueError("Matter history needs at least one determination")
    return inputs


def start_scenario(model):
    inputs = _source_check(model)
    model._matter_scenario = model.scenario
    model._matter_cases = {row["engagement_id"]: row for row in inputs["matters"]}
    model._matter_states = {
        eid: {name: ("PENDING" if name == "acceptance" else "PASS") for name in CONTROLS}
        for eid in model._matter_cases
    }
    model._matter_sources = {eid: {} for eid in model._matter_cases}
    for table in TABLES:
        model.tables[table]


class MatterMixin:
    def outcomes(self):
        if getattr(self, "_matter_scenario", None) != self.scenario:
            start_scenario(self)
        original = self.inputs["engagements"]
        allowed = []
        for engagement in original:
            eid = engagement["engagement_id"]
            if eid not in self._matter_cases or self.month < engagement["start_month"]:
                allowed.append(engagement)
                continue
            states = self._matter_states[eid]
            common = {
                "scenario": self.scenario,
                "period": period(self.month)[2],
                "unit": "advisory",
                "engagement_id": eid,
                "client_id": engagement["customer_id"],
                "fact_state": CLASSIFICATION,
            }
            for entry in self._matter_cases[eid]["events"]:
                if entry["month"] != self.month:
                    continue
                role, control, result = DECISIONS[entry["decision"]]
                source = self.event(
                    "MATTER_DETERMINATION",
                    f"{eid}-{entry['decision']}",
                    "advisory",
                    engagement_id=eid,
                    decision=entry["decision"],
                    responsible_role=role,
                    responsible_person=engagement["roles"][role],
                    reason=entry["reason"],
                    determination_state=CLASSIFICATION,
                )
                states[control] = result
                self._matter_sources[eid][control] = source
                if entry["decision"] == "RIGHTS_CLEARED":
                    states["acceptance"] = "PASS"
                    self._matter_sources[eid]["acceptance"] = source
                self.tables["matter_determinations"].append(
                    {
                        **common,
                        "decision": entry["decision"],
                        "control": control,
                        "result": result,
                        "role": role,
                        "person_id": engagement["roles"][role],
                        "reason": entry["reason"],
                        "source_id": source,
                    }
                )
            for control, state in states.items():
                source = self._matter_sources[eid].get(control) or self._matter_sources[eid].get(
                    "acceptance", "PENDING_ACCEPTANCE"
                )
                self.tables["matter_controls"].append(
                    {
                        **common,
                        "control": control,
                        "result": state,
                        "source_id": source,
                        "evidence_basis": "SYNTHETIC_CASE_DETERMINATION",
                    }
                )
            blocked = sorted(name for name, result in states.items() if result != "PASS")
            self.tables["matter_gate_decisions"].append(
                {
                    **common,
                    "gate_status": "BLOCKED" if blocked else "ALLOWED",
                    "blocked_controls": ";".join(blocked),
                    "work_allowed": not blocked,
                    "billing_allowed": not blocked,
                    "recognition_allowed": not blocked,
                    "prior_earned_revenue": "PRESERVED; hold prevents subsequent activity",
                }
            )
            if not blocked:
                allowed.append(engagement)
        # Restore even when the unmodified fee engine raises. A gate cannot alter
        # canonical prices, roles, scope, or the persistent source snapshot.
        self.inputs["engagements"] = allowed
        try:
            super().outcomes()
        finally:
            self.inputs["engagements"] = original


def validate(model):
    inputs = _source_check(model)
    selected = {row["engagement_id"] for row in inputs["matters"]}
    gates = {}
    for row in model.tables["matter_gate_decisions"]:
        key = (row["scenario"], row["period"], row["engagement_id"])
        if key in gates:
            raise ValueError("Duplicate matter gate decision")
        gates[key] = row
        expected = row["gate_status"] == "ALLOWED"
        if any(
            row[field] != expected
            for field in ("work_allowed", "billing_allowed", "recognition_allowed")
        ):
            raise ValueError("Matter gate permissions disagree")
    actions = {
        "MATTER_ACCEPTANCE",
        "DELIVERY_WORK",
        "OUTCOME_ACCEPTED",
        "VALUE_CERTIFIED",
        "CLIENT_TRANSFER_ACCEPTED",
    }
    for row in model.tables["events"]:
        if row["kind"] not in actions or row["unit"] != "advisory":
            continue
        eid = row.get("engagement_id", row["source_id"])
        if eid in selected:
            gate = gates.get((row["scenario"], row["period"], eid))
            if gate is None or gate["gate_status"] != "ALLOWED":
                raise ValueError(
                    "Missing or blocked matter gate produced work, billing or recognition"
                )
    expected = {
        (s, period(m)[2], e["engagement_id"])
        for s in model.policy["cases"]
        for e in model.inputs["engagements"]
        if e["engagement_id"] in selected
        for m in range(e["start_month"], 61)
    }
    if gates.keys() != expected:
        raise ValueError("Matter gate history incomplete")
    controls = {}
    for row in model.tables["matter_controls"]:
        key = (row["scenario"], row["period"], row["engagement_id"], row["control"])
        if key in controls:
            raise ValueError("Duplicate matter control evidence")
        controls[key] = row
    expected_controls = {(*key, control) for key in expected for control in CONTROLS}
    if controls.keys() != expected_controls:
        raise ValueError("Matter control evidence incomplete")
    engagements = {e["engagement_id"]: e for e in model.inputs["engagements"]}
    for case in inputs["matters"]:
        eid = case["engagement_id"]
        states = {name: ("PENDING" if name == "acceptance" else "PASS") for name in CONTROLS}
        by_month = {entry["month"]: entry for entry in case["events"]}
        for month in range(engagements[eid]["start_month"], 61):
            entry = by_month.get(month)
            if entry:
                _, control, result = DECISIONS[entry["decision"]]
                states[control] = result
                if entry["decision"] == "RIGHTS_CLEARED":
                    states["acceptance"] = "PASS"
            blocked = sorted(name for name, result in states.items() if result != "PASS")
            for scenario in model.policy["cases"]:
                key = (scenario, period(month)[2], eid)
                row = gates[key]
                if row["gate_status"] != ("BLOCKED" if blocked else "ALLOWED") or row[
                    "blocked_controls"
                ] != ";".join(blocked):
                    raise ValueError("Matter gate disagrees with original source determinations")
                if any(
                    controls[(*key, control)]["result"] != state
                    for control, state in states.items()
                ):
                    raise ValueError(
                        "Matter control result disagrees with original source determinations"
                    )
    for row in model.tables["matter_handover_evidence"]:
        if row["executed_tests"] != 7 or row["test_result"] != "PASS":
            raise ValueError("Client handover lacks successful executed tests")
    return {"selected_matters": len(selected), "monthly_gate_decisions": len(gates)}


WORKFLOW = '''"""Client-owned illustrative review aid; never autonomous operating control."""
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


def evaluate(client_id, asset_id, reading, stop=False):
    contract = json.loads(Path(__file__).with_name("contract.json").read_text())
    if client_id != contract["client_id"] or asset_id != contract["asset_id"]:
        raise PermissionError("Outside this client capability's explicit scope")
    if not isinstance(stop, bool):
        raise ValueError("Stop must be an explicit boolean")
    if stop:
        return "STOP"
    if isinstance(reading, bool) or not isinstance(reading, (str, int, float)):
        raise ValueError("Reading must be a finite numeric scalar")
    try:
        value = Decimal(str(reading))
    except InvalidOperation as exc:
        raise ValueError("Reading must be numeric") from exc
    if not value.is_finite() or value < 0:
        raise ValueError("Reading must be finite and nonnegative")
    return "REVIEW" if value >= Decimal(contract["threshold"]) else "MONITOR"
'''
CLIENT_TESTS = '''"""Disclosed client acceptance tests, not a private evaluator."""
import json
import unittest
from decimal import Decimal
from pathlib import Path
from workflow import evaluate

CONTRACT = json.loads(Path(__file__).with_name("contract.json").read_text())


class ClientAcceptanceTests(unittest.TestCase):
    def test_below_threshold(self):
        self.assertEqual(evaluate(CONTRACT["client_id"], CONTRACT["asset_id"], "0"), "MONITOR")

    def test_threshold_and_above(self):
        for value in (CONTRACT["threshold"], str(Decimal(CONTRACT["threshold"]) + 1)):
            self.assertEqual(evaluate(CONTRACT["client_id"], CONTRACT["asset_id"], value), "REVIEW")

    def test_stop_does_not_authorize_operation(self):
        self.assertEqual(evaluate(CONTRACT["client_id"], CONTRACT["asset_id"], None, stop=True), "STOP")

    def test_other_client_denied(self):
        with self.assertRaises(PermissionError):
            evaluate("UNAUTHORIZED-CLIENT", CONTRACT["asset_id"], "0")

    def test_other_asset_denied(self):
        with self.assertRaises(PermissionError):
            evaluate(CONTRACT["client_id"], "UNAUTHORIZED-ASSET", "0")

    def test_invalid_readings_denied(self):
        for value in ("NaN", "Infinity", "-1", "invalid", True, {}, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                evaluate(CONTRACT["client_id"], CONTRACT["asset_id"], value)

    def test_ambiguous_stop_denied(self):
        with self.assertRaises(ValueError):
            evaluate(CONTRACT["client_id"], CONTRACT["asset_id"], "0", stop="false")


if __name__ == "__main__":
    unittest.main()
'''
README = """# Client-owned review capability

This explicit synthetic example belongs only to the client and asset in contract.json. It contains no professional-plane methods, cross-client records, institutional sources or licensed product code. It does not grant an Atlas subscription.

Run `python -I -B -m unittest discover -s . -p test_workflow.py` to repeat all seven disclosed acceptance tests. A passing test is not production authorization.
"""
RUNBOOK = """# Client runbook

Owner: client operating owner. Maintainer: client designated service owner.

1. Confirm the intended client and asset in contract.json.
2. Validate source units, calibration and the threshold with the client owner before use.
3. Execute the disclosed tests and retain their results before adopting any version.
4. Supply only permitted client-local readings. REVIEW requests human review; MONITOR is not certification of safety or truth.
5. A stop request returns STOP; suspend reliance on the aid and follow the client's operating stop procedures. The capability never actuates equipment.
6. On error, source uncertainty or failed tests, stop using outputs and contact the owner.
7. Proposed changes require a new version, retained predecessor, client review and retest. Retire a rejected version; do not edit the accepted package in place.

No source ingestion, storage policy, network service or production security is supplied.
"""
PAYLOAD_FILES = {
    "workflow.py",
    "test_workflow.py",
    "README.md",
    "runbook.md",
    "contract.json",
    "dependencies.json",
}
PACKAGE_FILES = PAYLOAD_FILES | {"manifest.json", "verification.json"}
COMMAND = "python -I -B -m unittest discover -s . -p test_workflow.py"


def _json(value):
    return json.dumps(value, sort_keys=True, indent=2) + "\n"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_tests(package):
    # Only fixed, allowlisted payloads may reach this execution path.
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            ".",
            "-p",
            "test_workflow.py",
        ],
        cwd=package,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if (
        result.returncode
        or not re.search(r"Ran 7 tests? in ", result.stderr)
        or not result.stderr.rstrip().endswith("OK")
    ):
        raise ValueError("Client capability failed executed acceptance tests")


def _payload(client_id, asset_id):
    return {
        "workflow.py": WORKFLOW,
        "test_workflow.py": CLIENT_TESTS,
        "README.md": README,
        "runbook.md": RUNBOOK,
        "contract.json": _json(
            {
                "version": "1.0.0",
                "classification": CLASSIFICATION,
                "client_id": client_id,
                "asset_id": asset_id,
                "ownership": "CLIENT_OWNED",
                "human_owner": "Client operating owner",
                "maintenance_owner": "Client designated service owner",
                "scope": "Read-only threshold-review aid; no external connectors, credentials or actions",
                "threshold": "10.0",
            }
        ),
        "dependencies.json": _json(
            {
                "runtime": "Python >=3.11",
                "standard_library": ["decimal", "json", "pathlib", "unittest"],
                "external_packages": [],
                "network_access": False,
                "filesystem_scope": "Read own contract.json only",
            }
        ),
    }


def verify_matter_package(package, expected_client_id=None):
    package = Path(package)
    entries = list(package.iterdir())
    if {p.name for p in entries} != PACKAGE_FILES or any(
        p.is_symlink() or not p.is_file() for p in entries
    ):
        raise ValueError("Client package contains missing, extra or non-file material")
    manifest = json.loads((package / "manifest.json").read_text())
    contract = json.loads((package / "contract.json").read_text())
    if set(manifest) != {
        "package_id",
        "scenario",
        "engagement_id",
        "client_id",
        "accepted_period",
        "fact_state",
        "ownership",
        "files_sha256",
    }:
        raise ValueError("Client manifest contains unexpected or missing metadata")
    client_id = manifest["client_id"]
    if expected_client_id is not None and client_id != expected_client_id:
        raise ValueError("Client package belongs to a different client")
    if not re.fullmatch(r"SYN-CUSTOMER-\d{3}", client_id) or contract["client_id"] != client_id:
        raise ValueError("Client package identity is invalid")
    if manifest["fact_state"] != CLASSIFICATION or manifest["ownership"] != "CLIENT_OWNED":
        raise ValueError("Client transfer classification is invalid")
    eid, scenario = manifest["engagement_id"], manifest["scenario"]
    if (
        not re.fullmatch(r"ADV-2027-0[1-5]", eid)
        or scenario not in {"base", "downside", "expansion"}
        or manifest["package_id"] != f"{scenario}-{eid}-CLIENT-V1"
        or client_id != f"SYN-CUSTOMER-{int(eid.rsplit('-', 1)[1]):03}"
    ):
        raise ValueError("Client manifest is outside the selected matter and client perimeter")
    accepted = date.fromisoformat(manifest["accepted_period"])
    if not 2027 <= accepted.year <= 2031:
        raise ValueError("Client handover must lie within the synthetic forecast")
    asset_id = "SYN-CLIENT-ASSET-" + client_id.rsplit("-", 1)[1]
    for name, contents in _payload(client_id, asset_id).items():
        if (package / name).read_text() != contents:
            raise ValueError("Client payload differs from reviewed allowlisted templates")
    hashes = {name: _sha(package / name) for name in sorted(PACKAGE_FILES - {"manifest.json"})}
    if manifest["files_sha256"] != hashes:
        raise ValueError("Client manifest content hashes fail verification")
    verification = json.loads((package / "verification.json").read_text())
    if (
        set(verification)
        != {"command", "executed_tests", "status", "fact_state", "meaning", "payload_sha256"}
        or verification.get("status") != "PASS"
        or verification.get("executed_tests") != 7
        or verification.get("command") != COMMAND
        or verification.get("fact_state") != CLASSIFICATION
        or verification.get("payload_sha256")
        != {name: hashes[name] for name in sorted(PAYLOAD_FILES)}
    ):
        raise ValueError("Client package lacks valid executed test evidence")
    _run_tests(package)
    return manifest


def build_matter_packages(model, output):
    output = Path(output)
    selected = {row["engagement_id"] for row in _source_check(model)["matters"]}
    engagements = {e["engagement_id"]: e for e in model.inputs["engagements"]}
    model.tables["matter_handover_evidence"].clear()
    packages = []
    for event in model.tables["events"]:
        eid = event["source_id"]
        if event["kind"] != "CLIENT_TRANSFER_ACCEPTED" or eid not in selected:
            continue
        e = engagements[eid]
        check_transfer(e["transfer"])
        client_id = e["customer_id"]
        if (
            not re.fullmatch(r"ADV-\d{4}-\d{2}", eid)
            or event["scenario"] not in model.policy["cases"]
        ):
            raise ValueError("Unsafe package identity")
        package = output / "client-handovers" / event["scenario"] / eid
        package.mkdir(parents=True, exist_ok=False)
        for name, content in _payload(
            client_id, "SYN-CLIENT-ASSET-" + client_id.rsplit("-", 1)[1]
        ).items():
            (package / name).write_text(content)
        _run_tests(package)
        verification = {
            "command": COMMAND,
            "executed_tests": 7,
            "status": "PASS",
            "fact_state": CLASSIFICATION,
            "meaning": "Tests executed on fixed client payload; not production authorization or IAM",
            "payload_sha256": {name: _sha(package / name) for name in sorted(PAYLOAD_FILES)},
        }
        (package / "verification.json").write_text(_json(verification))
        manifest = {
            "package_id": f"{event['scenario']}-{eid}-CLIENT-V1",
            "scenario": event["scenario"],
            "engagement_id": eid,
            "client_id": client_id,
            "accepted_period": event["period"],
            "fact_state": CLASSIFICATION,
            "ownership": "CLIENT_OWNED",
            "files_sha256": {
                name: _sha(package / name) for name in sorted(PACKAGE_FILES - {"manifest.json"})
            },
        }
        (package / "manifest.json").write_text(_json(manifest))
        verify_matter_package(package, client_id)
        model.tables["matter_handover_evidence"].append(
            {
                "scenario": event["scenario"],
                "period": event["period"],
                "unit": "advisory",
                "engagement_id": eid,
                "client_id": client_id,
                "package_id": manifest["package_id"],
                "relative_path": package.relative_to(output).as_posix(),
                "manifest_sha256": _sha(package / "manifest.json"),
                "file_count": len(PACKAGE_FILES),
                "test_result": "PASS",
                "executed_tests": 7,
                "source_id": event["event_id"],
                "fact_state": CLASSIFICATION,
            }
        )
        packages.append(package)
    return packages
