"""Route reviewed LEG provision locators and DAT rights discovery without credit."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

from . import company_dat002_rights_scope_2027 as dat
from . import company_leg001_provision_overlay_2027 as leg
from . import documentary_283_route_reconciliation_v16 as prior
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .documentary_283_route_reconciliation_v12 import _pin

SCHEMA = "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V17"
BASE = "enterprise/generated/audit-suite"
LEG_SOURCE = "LEG001_PROVISION_OVERLAY_V1"
DAT_SOURCE = "DAT002_SELECTED_RIGHTS_SCOPE_V1"
LEG_LIMIT = (
    "One fictional 2027 selected customer-to-SHI-to-support chain, 34 selected term "
    "refs and 18 provision locators. Only 16 authored LEG001 PROVISION candidates gain "
    "locator discovery. The 2026 eCFR/HHS references do not establish 2027 law, "
    "enforceability, actual HIPAA applicability, contract execution, triggered matters "
    "or performance. All 66 LEG001 authored clauses remain unsupported and unrun."
)
DAT_LIMIT = (
    "One internally seeded fictional payload-free rights inquiry. Clean has five selected "
    "native originals; Messy has six including an OPEN premature no-record exception. "
    "Customer delegation, requester authority, complete designated-record-set/backup/"
    "subcontractor/disclosure population and qualified duty analysis remain unresolved. "
    "No actual request, response, rights completion, real PHI or audit credit."
)
V16_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V16_2026-10-01.json"
V16_RUN = f"{BASE}/documentary-283-route-reconciliation-v16-2026-10-01/main-run-v1/LEDGER.json"
V16_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v16-2026-10-01/"
    "independent-review-main-v1/REVIEW.json"
)
LEG_GAP = "enterprise/audit_suite/LEG001_66_CANDIDATE_GAP_2026-10-01.json"
LEG_GAP_MD = "enterprise/audit_suite/LEG001_66_CANDIDATE_GAP_2026-10-01.md"
LEG_RUN = f"{BASE}/company-leg001-provision-overlay-2027-10-01/main-run-v1"
LEG_REVIEW = (
    f"{BASE}/company-leg001-provision-overlay-2027-10-01/independent-review-main-v1/REVIEW.json"
)
LEG_GAP_REVIEW = (
    f"{BASE}/company-leg001-provision-overlay-2027-10-01/"
    "gap-status-correction-review-v1/REVIEW.json"
)
DAT_RUN = f"{BASE}/company-dat002-rights-scope-2027-2026-10-01/main-run-v1"
DAT_REVIEW = (
    f"{BASE}/company-dat002-rights-scope-2027-2026-10-01/independent-review-main-v1/REVIEW.json"
)
PINS = {
    "v16_ledger": {
        "scope": "repo",
        "path": V16_LEDGER,
        "sha256": "cd3b55409e9e0112b49d060cfbbacf329660422d0c4e1b2002ec220af5bad5a3",
    },
    "v16_run": {
        "scope": "private",
        "path": V16_RUN,
        "sha256": "cd3b55409e9e0112b49d060cfbbacf329660422d0c4e1b2002ec220af5bad5a3",
    },
    "v16_review": {
        "scope": "private",
        "path": V16_REVIEW,
        "sha256": "138bc8e7cd5e701d0507e4dcb6228364c3406aa097d12d14d9753c456ae60b34",
    },
    "leg_gap": {
        "scope": "repo",
        "path": LEG_GAP,
        "sha256": "2730d119873193a797156041005498b66bfc697546127d8c910e662c2e1725bf",
    },
    "leg_gap_md": {
        "scope": "repo",
        "path": LEG_GAP_MD,
        "sha256": "3727912e172dacfd4149991db1c91e4e84b7cd7e2f4a7948016986e4054ea915",
    },
    "leg_review": {
        "scope": "private",
        "path": LEG_REVIEW,
        "sha256": "359196741f6b82af450104997d78ebb301a6abcdcbfce29d9cf0ef47393c8583",
    },
    "leg_gap_review": {
        "scope": "private",
        "path": LEG_GAP_REVIEW,
        "sha256": "1e0b4008f8a684cb7ee191a8cbf8afc0bb6ac2395bec08da37abf85b67f0ae60",
    },
    "leg_manifest": {
        "scope": "private",
        "path": f"{LEG_RUN}/MANIFEST.json",
        "sha256": "add1462a98ea9b8cfc30a8195c8094f7213ea64c468c878d4c15151ac2abdc69",
    },
    "leg_receipt": {
        "scope": "private",
        "path": f"{LEG_RUN}/RECEIPT.json",
        "sha256": "ce1066519a21ab84a0a55c93ba143d637014dfac4d503126a0301e5ef22f187f",
    },
    "leg_db": {
        "scope": "private",
        "path": f"{LEG_RUN}/company.sqlite3",
        "sha256": "5ffb1eb1cc9429b87f60171fa2ff170d85be3b83f6854ebe246b3f0d59945d0e",
    },
    "leg_module": {
        "scope": "repo",
        "path": leg.SOURCE,
        "sha256": "0f3041f392b2d94393c9744fc20ca1ffd3e59912df7901cff994efa6a434c967",
    },
    "leg_spec": {
        "scope": "repo",
        "path": leg.SPEC,
        "sha256": "84e575a931ebe29e2146378af3998bd85c039709570f302517cada9fdfed64da",
    },
    "dat_review": {
        "scope": "private",
        "path": DAT_REVIEW,
        "sha256": "7c244ae5938868b1caf97500682a8f4cad1402d59e29a45c08fb8110e388763e",
    },
    "dat_manifest": {
        "scope": "private",
        "path": f"{DAT_RUN}/MANIFEST.json",
        "sha256": "222b21ad5a90e05fb1c690951e7a94537148a682a69a39a661fbc0fd0ff2f91f",
    },
    "dat_receipt": {
        "scope": "private",
        "path": f"{DAT_RUN}/RECEIPT.json",
        "sha256": "55502c4210f1855e570352d4972c002ca8726c74db551691e1e89eb4230064ad",
    },
    "dat_db": {
        "scope": "private",
        "path": f"{DAT_RUN}/company.sqlite3",
        "sha256": "07deca8ba563281439167f5b274364942dab9a9fdc96b01209a722d3f13e1a44",
    },
    "dat_module": {
        "scope": "repo",
        "path": dat.SOURCE_REFERENCE,
        "sha256": "fc0ce32741fafe0946f04865c2b8c21c7236a31ea237576ca245c345603869f1",
    },
}
P1_FREEZE = prior.P1_FREEZE
IDENTITY = prior.IDENTITY
DAT_TASKS = dat.DISCOVERY_TASKS
LEG_PRECORRECTION_GAP_SHA256 = "3f1a0991e40ee756556d9287c15e21d29d42b6543081d5bdcfd950b7b7b28071"


class V17ReconciliationError(prior.V16ReconciliationError):
    """Reviewed V16, LEG or DAT source, exact task, or no-credit boundary changed."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _leg_tasks(gap: dict, previous: dict) -> tuple[str, ...]:
    if (
        gap.get("schema") != "SH_LEG001_66_AUTHORED_CANDIDATE_GAP_V1"
        or gap.get("counts_per_side", {}).get("unsupported_exact_clauses") != 66
        or gap["counts_per_side"].get("bounded_provision_candidates") != 16
        or gap["counts_per_side"].get("unmodeled_in_this_iteration") != 50
        or gap.get("p1_freeze") != P1_FREEZE
        or gap.get("audit_task_credit") is not False
        or gap.get("source_complete") is not False
    ):
        raise V17ReconciliationError("Reviewed LEG exact gap denominator differs")
    task_lists = []
    for side in "AB":
        rows = gap["rows_by_side"][side]
        selected = [row for row in rows if row["new_overlay_cohort"]]
        old = {
            row["task_id"]: row
            for row in previous["rows"]
            if row["side"] == side and row["control_id"] == "SH-LEG-001"
        }
        if (
            len(rows) != 66
            or len(selected) != 16
            or len({row["task_id"] for row in rows}) != 66
            or len(old) != 72
            or any(
                row["new_overlay_status"] != "SELECTED_NATIVE_LOCATOR_CANDIDATE_NOT_ROUTED"
                or row["request_group_id"] != "SH-LEG-001/PROVISION"
                or row["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
                or row["v16_existing_targeted_source_ids"] != []
                or row["audit_task_credit"] is not False
                or old[row["task_id"]]["authored_test_clause"] != row["authored_test_clause"]
                or old[row["task_id"]]["requirement_ids"] != row["requirement_ids"]
                for row in selected
            )
        ):
            raise V17ReconciliationError("Exact 16 LEG provision candidate rows differ")
        task_lists.append(tuple(row["task_id"] for row in selected))
    if task_lists[0] != task_lists[1]:
        raise V17ReconciliationError("LEG paired provision candidate tasks differ")
    return task_lists[0]


def _native_refs(receipt: dict, scenario: str, branch: str, count: int) -> list[dict]:
    records = receipt.get("records", {}).get(scenario)
    if (
        not isinstance(records, list)
        or len(records) != count
        or any(
            row.get("company") != leg.COMPANY
            or row.get("branch") != branch
            or row.get("version") != 1
            or row.get("origin") != "AUTHORED_TRAINING_SOURCE"
            or any(not row.get(key) for key in IDENTITY)
            for row in records
        )
    ):
        raise V17ReconciliationError("Selected exact native branch refs differ")
    return [{key: row[key] for key in IDENTITY} for row in records]


def _selected_refs(leg_receipt: dict, dat_receipt: dict, gap: dict, previous: dict) -> dict:
    tasks = _leg_tasks(gap, previous)
    if (
        leg_receipt.get("schema") != leg.SCHEMA
        or leg_receipt.get("branches") != {"CLEAN": "LEGOV-CLEAN", "MESSY": "LEGOV-MESSY"}
        or leg_receipt.get("source_pins")
        != {
            "repo://" + leg.SPEC: leg.SPEC_SHA256,
            "repo://" + leg.APPOINTMENTS: leg.APPOINTMENTS_SHA256,
        }
        | {"private://" + key: value for key, value in leg.PRIVATE_PINS.items()}
        or leg_receipt.get("selected_term_count_per_branch") != 34
        or leg_receipt.get("provision_locator_count_per_branch") != 18
        or leg_receipt.get("bounded_authored_provision_candidates_per_side") != 16
        or leg_receipt.get("remaining_unmodeled_authored_candidates_per_side") != 50
        or leg_receipt.get("open_historical_exception_ids")
        != {"CLEAN": [], "MESSY": leg.OPEN_EXCEPTIONS}
        or leg_receipt.get("real_hipaa_applicability") != "UNDETERMINED"
        or any(
            leg_receipt.get(key) is not False
            for key in (
                "2027_legal_text_verified",
                "actual_phi",
                "real_contract_executed",
                "outside_message_sent",
                "source_complete",
                "audit_task_credit",
            )
        )
        or dat_receipt.get("schema") != dat.SCHEMA
        or dat_receipt.get("branches") != dat.BRANCHES
        or dat_receipt.get("discovery_only_task_ids_per_side") != list(DAT_TASKS)
        or dat_receipt.get("native_versions_per_branch") != {"CLEAN": 5, "MESSY": 6}
        or dat_receipt.get("open_scope_exception_ids") != {"CLEAN": [], "MESSY": [dat.EXCEPTION_ID]}
        or dat_receipt.get("actual_requests_or_external_responses") != 0
        or dat_receipt.get("accepted_amendments_or_accounting_completions") != 0
        or any(
            dat_receipt.get(key) is not False
            for key in (
                "complete_record_or_period_population",
                "actual_phi_or_ba_claim",
                "fresh_audit_pair_created",
                "audit_task_credit",
            )
        )
    ):
        raise V17ReconciliationError("Selected LEG/DAT source scope or no-credit boundary differs")
    result = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        leg_rows = _native_refs(leg_receipt, scenario, leg_receipt["branches"][scenario], 20)
        dat_rows = _native_refs(
            dat_receipt,
            scenario,
            dat_receipt["branches"][scenario],
            5 if scenario == "CLEAN" else 6,
        )
        leg_map = {(row["system"], row["record"]): row for row in leg_rows}
        if len(leg_map) != 20 or len({(r["system"], r["record"]) for r in dat_rows}) != len(
            dat_rows
        ):
            raise V17ReconciliationError("Selected native roster duplicated")
        if tuple(key for key in leg_map if key[0] == "provision_locator") != tuple(
            ("provision_locator", f"PROVISION-{n:02d}") for n in range(1, 19)
        ):
            raise V17ReconciliationError("LEG exact 18-locator roster differs")
        common = [leg_map[("obligation_snapshot", "CHAIN-TERMS-01")]]
        finish = [leg_map[("overlay_reconciliation", "LEG001-PROVISION-OVERLAY-01")]]
        leg_by_task = {}
        for task in tasks:
            if task.endswith("ACTION-H-LEGAL-STATUS"):
                indices = (16, 17, 18)
            else:
                provision = task.rsplit(":", 1)[1]
                if provision not in leg.PROVISION_IDS[:15]:
                    raise V17ReconciliationError("LEG exact authored provision locator differs")
                indices = (leg.PROVISION_IDS.index(provision) + 1,)
            leg_by_task[task] = [
                *common,
                *(leg_map[("provision_locator", f"PROVISION-{index:02d}")] for index in indices),
                *finish,
            ]
        result[side] = {"leg": leg_by_task, "dat": dat_rows}
    return result


def _extend(previous: dict, leg_receipt: dict, dat_receipt: dict, gap: dict, freeze: dict) -> dict:
    """Append only exact 16 LEG and two DAT selected native leads per side."""
    if (
        previous.get("schema") != prior.SCHEMA
        or previous.get("as_of") != "2026-10-01"
        or previous.get("p1_freeze") != freeze
        or previous.get("audit_task_credit") is not False
        or previous.get("active_pair_mutated") is not False
        or len(previous.get("rows", [])) != 566
        or previous.get("active_p1_tasks")
        != {
            side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
            for side in "AB"
        }
        or any(
            previous["counts"][side]["targeted_integrated_route_count"] != 183
            or previous["counts"][side]["classifications"]
            != {
                "DESIGN_CONTEXT_ONLY": 21,
                "SOURCE_CANDIDATE_PARTIAL": 141,
                "UNSUPPORTED_EXACT_CLAUSE": 121,
            }
            for side in "AB"
        )
    ):
        raise V17ReconciliationError("Reviewed V16 prefix or frozen P1 differs")
    refs = _selected_refs(leg_receipt, dat_receipt, gap, previous)
    leg_tasks = set(refs["A"]["leg"])
    targets = leg_tasks | set(DAT_TASKS)
    if len(leg_tasks) != 16 or len(targets) != 18:
        raise V17ReconciliationError("Exact 18 selected task identities differ")
    rows = []
    for old in previous["rows"]:
        row = deepcopy(old)
        leg_selected = old["task_id"] in leg_tasks
        dat_selected = old["task_id"] in DAT_TASKS
        selected_source = LEG_SOURCE if leg_selected else DAT_SOURCE if dat_selected else None
        if selected_source:
            if (
                old["targeted_integrated_source_ids"] != []
                or old["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
                or old["test_gate_basis"] != "AUTHORED_TASK_CLAUSE"
                or old["authored_test_clause"] != old["remaining_test_gate"]
                or old["current_status"] != "NOT_STARTED"
                or old["current_conclusion"] != "NOT_RUN"
                or old["audit_task_credit"] is not False
                or old["control_id"] != ("SH-LEG-001" if leg_selected else "SH-DAT-002")
            ):
                raise V17ReconciliationError("Selected authored route/untargeted gate differs")
            row["targeted_integrated_source_ids"].append(selected_source)
        row["v17_reviewed_source_ids"] = [selected_source] if selected_source else []
        row["v17_source_limits"] = (
            {selected_source: LEG_LIMIT if leg_selected else DAT_LIMIT} if selected_source else {}
        )
        row["v17_source_record_refs"] = (
            {
                selected_source: refs[old["side"]]["leg"][old["task_id"]]
                if leg_selected
                else refs[old["side"]]["dat"]
            }
            if selected_source
            else {}
        )
        allowed = {"targeted_integrated_source_ids"} if selected_source else set()
        if any(row[key] != value for key, value in old.items() if key not in allowed):
            raise V17ReconciliationError("V16 row prefix field changed")
        rows.append(row)
    counts = {}
    for side in "AB":
        subset = [row for row in rows if row["side"] == side]
        selected = [row for row in subset if row["v17_reviewed_source_ids"]]
        classes = dict(sorted(Counter(row["classification"] for row in subset).items()))
        if (
            len(subset) != 283
            or len({row["task_id"] for row in subset}) != 283
            or len(selected) != 18
            or {row["task_id"] for row in selected} != targets
            or sum(bool(row["targeted_integrated_source_ids"]) for row in subset) != 201
            or classes != previous["counts"][side]["classifications"]
            or any(
                row["current_status"] != "NOT_STARTED"
                or row["current_conclusion"] != "NOT_RUN"
                or row["audit_task_credit"] is not False
                for row in subset
            )
        ):
            raise V17ReconciliationError(
                "Exact V17 route count/classification/no-credit gate differs"
            )
        counts[side] = {
            **deepcopy(previous["counts"][side]),
            "targeted_integrated_route_count": 201,
            "v17_new_selected_leg_provision_authored_leads": 16,
            "v17_new_selected_dat_rights_authored_leads": 2,
            "v17_new_distinct_targeted_routes": 18,
            "v17_new_classification_promotions": 0,
        }
    if counts["A"] != counts["B"]:
        raise V17ReconciliationError("Paired V17 route counts differ")
    pins = {**previous["source_pins"], **PINS}
    return {
        **previous,
        "schema": SCHEMA,
        "as_of": "2026-10-01",
        "v16_prefix_sha256": PINS["v16_ledger"]["sha256"],
        "source_pins": pins,
        "source_pins_sha256": hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest(),
        "reviewed_source_roster": {
            **previous["reviewed_source_roster"],
            "additional_selected_leg_provision_overlay_versions": 40,
            "additional_selected_dat_rights_scope_versions": 11,
        },
        "counts": counts,
        "rows": rows,
        "limits": [
            *previous["limits"],
            "Only 16 LEG001 PROVISION authored and two DAT002 rights/164.501 authored routes "
            "gain a reviewed selected company-native discovery lead per side. The other "
            "265 V16 routes per side retain every prior row field; all 121 authored "
            "unsupported clauses and 409 P1 tasks per side remain unrun.",
            LEG_LIMIT,
            DAT_LIMIT,
            "No legal applicability or 2027 text conclusion, actual PHI/BA, completed "
            "rights action, clause satisfaction, source completeness, task credit, fresh "
            "pair, Key, grade or Atlas write.",
        ],
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V17ReconciliationError("Frozen P1 inventory differs")
    paths = {name: _pin(repository, private, entry) for name, entry in PINS.items()}
    previous = json.loads(paths["v16_ledger"].read_text())
    if previous != json.loads(paths["v16_run"].read_text()):
        raise V17ReconciliationError("Tracked/private reviewed V16 bytes differ")
    route_review = json.loads(paths["v16_review"].read_text())
    leg_review = json.loads(paths["leg_review"].read_text())
    leg_gap_review = json.loads(paths["leg_gap_review"].read_text())
    dat_review = json.loads(paths["dat_review"].read_text())
    leg_manifest = json.loads(paths["leg_manifest"].read_text())
    dat_manifest = json.loads(paths["dat_manifest"].read_text())
    if (
        route_review.get("schema") != "SH_INDEPENDENT_GOV_ROUTE_V16_MAIN_REVIEW_V1"
        or route_review.get("verdict") != "PASS_MAIN_SELECTED_GOV_LEAD_NO_AUDIT_CREDIT"
        or route_review.get("output_sha256", {}).get("LEDGER.json") != PINS["v16_ledger"]["sha256"]
        or route_review.get("p1_freeze") != freeze
        or route_review.get("audit_task_credit") is not False
        or route_review.get("source_complete") is not False
        or leg_review.get("schema") != "SH_INDEPENDENT_LEG001_PROVISION_OVERLAY_MAIN_REVIEW_V1"
        or leg_review.get("verdict") != "PASS_MAIN_SELECTED_LOCATORS_OPEN_NO_AUDIT_CREDIT"
        or leg_review.get("main_run_sha256")
        != {
            "MANIFEST.json": PINS["leg_manifest"]["sha256"],
            "RECEIPT.json": PINS["leg_receipt"]["sha256"],
            "company.sqlite3": PINS["leg_db"]["sha256"],
        }
        or leg_review.get("corrected_gap_report_sha256", {}).get("JSON")
        != LEG_PRECORRECTION_GAP_SHA256
        or leg_gap_review.get("schema") != "SH_INDEPENDENT_LEG001_GAP_STATUS_CORRECTION_V1"
        or leg_gap_review.get("verdict") != "PASS_DERIVED_LEDGER_LABEL_ONLY_NO_AUDIT_CREDIT"
        or leg_gap_review.get("prior_source_review_sha256") != PINS["leg_review"]["sha256"]
        or leg_gap_review.get("tracked_gap_json_sha256") != PINS["leg_gap"]["sha256"]
        or leg_gap_review.get("tracked_gap_markdown_sha256") != PINS["leg_gap_md"]["sha256"]
        or leg_gap_review.get("source_complete") is not False
        or leg_gap_review.get("audit_task_credit") is not False
        or leg_review.get("source_complete") is not False
        or leg_review.get("audit_task_credit") is not False
        or dat_review.get("schema") != "SH_INDEPENDENT_DAT002_RIGHTS_SCOPE_MAIN_REVIEW_V1"
        or dat_review.get("verdict") != "PASS_MAIN_SELECTED_SOURCE_NO_AUDIT_CREDIT"
        or dat_review.get("main_run_sha256")
        != {
            "MANIFEST.json": PINS["dat_manifest"]["sha256"],
            "RECEIPT.json": PINS["dat_receipt"]["sha256"],
            "company.sqlite3": PINS["dat_db"]["sha256"],
        }
        or dat_review.get("source_complete") is not False
        or dat_review.get("audit_task_credit") is not False
        or any(
            manifest.get("audit_task_credit") is not False
            for manifest in (leg_manifest, dat_manifest)
        )
        or leg_manifest.get("native_version_count") != 40
        or leg_manifest.get("receipt_sha256") != PINS["leg_receipt"]["sha256"]
        or leg_manifest.get("company_db_sha256") != PINS["leg_db"]["sha256"]
        or leg_manifest.get("module_sha256") != PINS["leg_module"]["sha256"]
        or leg_manifest.get("spec_sha256") != PINS["leg_spec"]["sha256"]
        or dat_manifest.get("native_version_count") != 11
        or dat_manifest.get("receipt_sha256") != PINS["dat_receipt"]["sha256"]
        or dat_manifest.get("company_db_sha256") != PINS["dat_db"]["sha256"]
        or dat_manifest.get("module_sha256") != PINS["dat_module"]["sha256"]
    ):
        raise V17ReconciliationError("Independent V16/LEG/DAT review join differs")
    leg_receipt = leg.verify(private / LEG_RUN, repository=repository, private_repository=private)
    dat.verify(private / DAT_RUN, repository=repository, private_repository=private)
    dat_receipt = json.loads(paths["dat_receipt"].read_text())
    if leg_receipt != json.loads(paths["leg_receipt"].read_text()):
        raise V17ReconciliationError("Verified LEG receipt differs from pinned bytes")
    gap = json.loads(paths["leg_gap"].read_text())
    result = _extend(previous, leg_receipt, dat_receipt, gap, freeze)
    if _p1_inventory(private) != freeze or any(
        _digest(path) != PINS[name]["sha256"] for name, path in paths.items()
    ):
        raise V17ReconciliationError("Pinned V17 source or P1 changed during read-only build")
    return result


def markdown(result: dict) -> str:
    counts = result["counts"]["A"]
    lines = [
        "# Paired 283-route selected LEG/DAT discovery reconciliation V17",
        "",
        "Sixteen SH-LEG-001 authored provision-status requests and two SH-DAT-002 "
        "authored rights/record-scope requests per side gain exact reviewed company-native "
        "selected leads. The other 265 routes per side preserve every V16 row field.",
        "",
        "| Measure per side | Count |",
        "| --- | ---: |",
        f"| Distinct targeted routes | {counts['targeted_integrated_route_count']} |",
        "| New LEG authored locator leads | 16 |",
        "| New DAT authored inquiry leads | 2 |",
        "| New classification promotions | 0 |",
        "| Unsupported exact clauses | 121 |",
        "| Frozen P1 tasks NOT_STARTED/NOT_RUN | 409 |",
        "",
        "The LEG source has 18 provision locators but does not establish 2027 legal text, "
        "actual applicability, contract execution or performance. Its 164.509 status "
        "remains held for qualified review. The DAT source is one internally seeded "
        "payload-free inquiry with incomplete rights authority and record population; "
        "Messy retains its OPEN premature no-record exception.",
        "",
        "Every authored clause remains UNSUPPORTED_EXACT_CLAUSE and unrun. No actual "
        "PHI/BA status, external request or response, rights completion, accepted N/A, "
        "audit task credit, fresh pair, Key, grade or Atlas write follows.",
        "",
    ]
    return "\n".join(lines)
