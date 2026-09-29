"""Prospective inert software-install policy exercise in an independent company store.

The fixture is a digest of text. No executable file is created or run, and decisions
describe a simulated local policy check rather than an operating endpoint control.
"""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .company_backup_runtime import private, require
from .company_store import CompanyStore, _id, _now, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

QUALIFICATION = "FICTIONAL_REFERENCE_EXERCISE_NOT_DEPLOYMENT"
SYSTEMS = (
    "software_definition",
    "software_inventory",
    "software_approval",
    "software_operation",
    "software_detection",
    "software_exception",
    "software_reconciliation",
)
APPROVED_DIGEST = sha(b"inert training fixture: approved update v2")
UNAPPROVED_DIGEST = sha(b"inert training fixture: unapproved candidate")


def _pin(row):
    return {key: row[key] for key in ("company", "branch", "system", "record", "version", "sha256")}


def _stamp(value):
    return value.isoformat(timespec="microseconds")


def decide_install(definition, *, asset_id, fixture_sha256, simulated_at, exception=None):
    """Evaluate only the declared inert digest, exact asset and local time window."""
    require(asset_id in definition["declared_assets"], "Undeclared local asset")
    require(
        isinstance(fixture_sha256, str)
        and len(fixture_sha256) == 64
        and all(char in "0123456789abcdef" for char in fixture_sha256),
        "Exact fixture digest required",
    )
    at = _time(simulated_at)
    if fixture_sha256 == definition["approved_fixture_sha256"]:
        return "ALLOWED_APPROVED_DIGEST"
    if exception and (
        exception["asset_id"] == asset_id
        and exception["fixture_sha256"] == fixture_sha256
        and exception["decision"] == "AUTHORIZED_LOCAL_SIMULATED_POLICY_EXCEPTION"
    ):
        starts, expires = _time(exception["starts_at"]), _time(exception["expires_at"])
        require(starts < expires, "Invalid local exception window")
        if starts <= at < expires:
            return "ALLOWED_BY_ACTIVE_EXACT_LOCAL_EXCEPTION"
        if at >= expires:
            return "DENIED_EXPIRED_LOCAL_EXCEPTION"
    return "DENIED_UNAPPROVED_DIGEST"


def run_exercise(
    destination: Path,
    *,
    company_id: str,
    branch_id: str,
    exercise_id: str,
    owner_id: str,
    approver_id: str,
    responder_id: str,
):
    """Publish one new, locally qualified source history before any audit collection."""
    destination = Path(destination)
    private(destination.parent, True)
    require(
        destination.is_absolute()
        and destination == destination.resolve()
        and not destination.exists(),
        "New canonical private destination required",
    )
    for value in (company_id, branch_id, exercise_id, owner_id, approver_id, responder_id):
        _id(value)
    require(
        len({owner_id, approver_id, responder_id}) == 3,
        "Distinct local owner, approver and responder required",
    )
    started = datetime.now(UTC)
    simulated = [_stamp(started + timedelta(minutes=minute)) for minute in (0, 1, 2, 3, 4, 5, 6)]
    code_sha256 = sha(Path(__file__).read_bytes())
    provenance = {
        "source_reference": exercise_id,
        "classification": QUALIFICATION,
        "authority_basis": (
            "Distinct local exercise roles; no corporate appointment or deployment acceptance"
        ),
        "asset_basis": "Two explicitly declared inert local assets, not enterprise discovery",
        "site_basis": "No operation at Reno, Boise or a provider is asserted",
        "clock_basis": (
            "Exercise decisions use prospective simulated times; "
            "source event_at is real recording time"
        ),
        "code_sha256": code_sha256,
        "control_ids": ["SH-CFG-002"],
    }
    with tempfile.TemporaryDirectory(
        dir=destination.parent, prefix="software-install-stage-"
    ) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        for system in SYSTEMS:
            store.register_system(company_id, branch_id, system, owner_id)
        pins = {}

        def append(system, record, body):
            at = _now()
            source = {
                "exercise_id": exercise_id,
                "qualification": QUALIFICATION,
                "recorded_at": at,
                **body,
            }
            row = store.append_version(
                company_id,
                branch_id,
                system,
                record,
                expected_version=0,
                command_id="SWI-" + sha(encoded([exercise_id, system, record]))[:48],
                event_at=at,
                available_at=at,
                content=encoded(source),
                provenance=provenance,
            )
            pins[record] = _pin(row)
            return pins[record]

        definition_body = {
            "declared_assets": ["LOCAL-ASSET-1", "LOCAL-ASSET-2"],
            "software": "inert-training-component",
            "initial_version": "fixture-v1",
            "approved_update_version": "fixture-v2",
            "approved_fixture_sha256": APPROVED_DIGEST,
            "unapproved_fixture_sha256": UNAPPROVED_DIGEST,
            "fixture_kind": "UTF8_TEXT_DIGEST_ONLY_NO_EXECUTABLE_FILE",
            "policy_id": "LOCAL-INSTALL-RULE-1",
            "policy_revision": 1,
            "policy": (
                "Only approved digest/version may be installed; an exact, active local "
                "exception permits a simulated policy decision for one asset and digest"
            ),
            "owner_id": owner_id,
            "approver_id": approver_id,
            "responder_id": responder_id,
            "simulated_clock_start": simulated[0],
            "professional_acceptance": "NOT_PERFORMED",
        }
        definition = append("software_definition", "DEFINITION", definition_body)
        initial_assets = [
            {"asset_id": asset, "software_version": "fixture-v1"}
            for asset in definition_body["declared_assets"]
        ]
        inventory = append(
            "software_inventory",
            "INVENTORY-INITIAL",
            {
                "definition_pin": definition,
                "assets": initial_assets,
                "inventory_basis": "EXPLICIT_LOCAL_DECLARATION_NOT_ENTERPRISE_ASSET_CENSUS",
            },
        )
        approval = append(
            "software_approval",
            "UPDATE-APPROVAL",
            {
                "definition_pin": definition,
                "inventory_pin": inventory,
                "actor_id": approver_id,
                "asset_id": "LOCAL-ASSET-1",
                "software_version": "fixture-v2",
                "fixture_sha256": APPROVED_DIGEST,
                "simulated_at": simulated[0],
                "decision": "APPROVED_LOCAL_UPDATE",
                "authority_limit": "Local inert fixture only",
            },
        )
        update = append(
            "software_operation",
            "APPROVED-UPDATE",
            {
                "definition_pin": definition,
                "prior_inventory_pin": inventory,
                "approval_pin": approval,
                "actor_id": owner_id,
                "asset_id": "LOCAL-ASSET-1",
                "from_version": "fixture-v1",
                "to_version": "fixture-v2",
                "fixture_sha256": APPROVED_DIGEST,
                "simulated_at": simulated[1],
                "decision": "APPROVED_LOCAL_UPDATE_RECORDED",
                "effect": "INERT_INVENTORY_VERSION_CHANGE_ONLY",
            },
        )
        updated_assets = [
            {
                **asset,
                "software_version": (
                    "fixture-v2"
                    if asset["asset_id"] == "LOCAL-ASSET-1"
                    else asset["software_version"]
                ),
            }
            for asset in initial_assets
        ]
        updated_inventory = append(
            "software_inventory",
            "INVENTORY-AFTER-UPDATE",
            {
                "definition_pin": definition,
                "prior_inventory_pin": inventory,
                "update_pin": update,
                "assets": updated_assets,
                "inventory_basis": "EXPLICIT_LOCAL_DECLARATION_NOT_ENTERPRISE_ASSET_CENSUS",
            },
        )
        denied = append(
            "software_operation",
            "UNAPPROVED-ATTEMPT",
            {
                "definition_pin": definition,
                "inventory_pin": updated_inventory,
                "actor_id": owner_id,
                "asset_id": "LOCAL-ASSET-1",
                "fixture_sha256": UNAPPROVED_DIGEST,
                "simulated_at": simulated[2],
                "decision": decide_install(
                    definition_body,
                    asset_id="LOCAL-ASSET-1",
                    fixture_sha256=UNAPPROVED_DIGEST,
                    simulated_at=simulated[2],
                ),
                "effect": "NO_OS_INSTALL_NO_EXECUTION",
            },
        )
        detection = append(
            "software_detection",
            "BLOCK-ALERT-RESPONSE",
            {
                "definition_pin": definition,
                "attempt_pin": denied,
                "alert_id": "LOCAL-INSTALL-ALERT-1",
                "detected_at": simulated[2],
                "responded_at": simulated[3],
                "responder_id": responder_id,
                "triage": "UNAPPROVED_DIGEST_MATCHED_LOCAL_RULE",
                "response": "BLOCK_RETAINED_AND_LOCAL_OWNER_NOTIFIED",
                "effect": "SIMULATED_ALERT_AND_TRIAGE_ONLY",
            },
        )
        request = append(
            "software_exception",
            "EXCEPTION-REQUEST",
            {
                "definition_pin": definition,
                "attempt_pin": denied,
                "detection_pin": detection,
                "requester_id": owner_id,
                "asset_id": "LOCAL-ASSET-1",
                "fixture_sha256": UNAPPROVED_DIGEST,
                "requested_at": simulated[3],
                "rationale": "Exercise the bounded local exception path for an inert fixture",
                "status": "REQUESTED_LOCAL_ONLY",
            },
        )
        exception_body = {
            "definition_pin": definition,
            "request_pin": request,
            "approver_id": approver_id,
            "asset_id": "LOCAL-ASSET-1",
            "fixture_sha256": UNAPPROVED_DIGEST,
            "starts_at": simulated[4],
            "expires_at": simulated[6],
            "decision": "AUTHORIZED_LOCAL_SIMULATED_POLICY_EXCEPTION",
            "authority_limit": (
                "No real executable installation, enterprise approval or deployed control"
            ),
        }
        exception = append("software_exception", "EXCEPTION-DECISION", exception_body)
        allowed = append(
            "software_operation",
            "EXCEPTION-RETRY",
            {
                "definition_pin": definition,
                "inventory_pin": updated_inventory,
                "exception_pin": exception,
                "actor_id": owner_id,
                "asset_id": "LOCAL-ASSET-1",
                "fixture_sha256": UNAPPROVED_DIGEST,
                "simulated_at": simulated[5],
                "decision": decide_install(
                    definition_body,
                    asset_id="LOCAL-ASSET-1",
                    fixture_sha256=UNAPPROVED_DIGEST,
                    simulated_at=simulated[5],
                    exception=exception_body,
                ),
                "effect": "SIMULATED_POLICY_DECISION_NO_OS_INSTALL_NO_EXECUTION",
            },
        )
        expired = append(
            "software_operation",
            "POST-EXPIRY-ATTEMPT",
            {
                "definition_pin": definition,
                "inventory_pin": updated_inventory,
                "exception_pin": exception,
                "prior_attempt_pin": allowed,
                "actor_id": owner_id,
                "asset_id": "LOCAL-ASSET-1",
                "fixture_sha256": UNAPPROVED_DIGEST,
                "simulated_at": simulated[6],
                "decision": decide_install(
                    definition_body,
                    asset_id="LOCAL-ASSET-1",
                    fixture_sha256=UNAPPROVED_DIGEST,
                    simulated_at=simulated[6],
                    exception=exception_body,
                ),
                "effect": "NO_OS_INSTALL_NO_EXECUTION",
            },
        )
        reconciliation = append(
            "software_reconciliation",
            "LOCAL-COVERAGE",
            {
                "definition_pin": definition,
                "initial_inventory_pin": inventory,
                "updated_inventory_pin": updated_inventory,
                "tested_asset_ids": ["LOCAL-ASSET-1"],
                "untested_declared_asset_ids": ["LOCAL-ASSET-2"],
                "attempt_pins": [denied, allowed, expired],
                "detection_pin": detection,
                "exception_pin": exception,
                "coverage_limit": (
                    "One of two declared inert assets tested; "
                    "no representative operating population"
                ),
            },
        )
        receipt = {
            "status": "PROSPECTIVE_LOCAL_SOURCE_ONLY",
            "company": company_id,
            "branch": branch_id,
            "exercise_id": exercise_id,
            "qualification": QUALIFICATION,
            "code_sha256": code_sha256,
            "native_pins": pins,
            "reconciliation_pin": reconciliation,
            "limits": [
                "Source event_at and availability are real recording times; "
                "decision clocks are simulated.",
                "No executable file was installed or run.",
                "No Reno, Boise, provider or enterprise endpoint operation is asserted.",
                "No 2027 operating-period performance, audit task credit "
                "or professional acceptance.",
            ],
        }
        receipt_path = stage / "SOURCE-RECEIPT.json"
        receipt_path.write_bytes(encoded(receipt))
        receipt_path.chmod(0o600)
        publish(stage, destination)
    return receipt
