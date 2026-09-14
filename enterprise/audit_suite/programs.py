"""Build private source-verified training packs from the existing CCF preparation.

Retained originals are checked by the original compiler. Candidate duties stay
candidate duties: this adapter supplies neither professional mapping acceptance
nor redistribution rights in the underlying standard text.
"""

import hashlib
import json
from pathlib import Path

from enterprise.ccf.assurance.actions import plan
from enterprise.ccf.registry import compile_registry, digest

from .generation import private_json
from .store import DomainError

ISM_SHA256 = "7af2ba74079dcbdd02265b43a416da1cb2472f53a7128670353f4200f0f707ef"
ISM_VERSION = "2026.09.4"


def dependency_tasks(scope: dict, program_pack: dict | None) -> list[dict]:
    """Keep source/service applicability gates visible as separate reviewer work."""
    if not program_pack:
        return []
    selected = set(scope["programs"])
    names = (["baseline"] if selected.intersection({"SOC2", "HIPAA"}) else []) + sorted(
        selected.intersection({"ISO27001", "ISO42001", "C5"})
    )
    gates = {}
    for name in names:
        for gate in program_pack["selections"][name].get("dependency_gates", []):
            old = gates.get(gate["id"])
            if old is not None and old != gate:
                raise DomainError("Conflicting source dependency definitions")
            gates[gate["id"]] = gate
    return [
        {
            "id": "TASK-" + gate["id"],
            "title": gate["title"],
            "kind": "SCOPE_DEPENDENCY",
            "test": gate["acceptance"],
            "responsible_role": gate["owner"],
            "scope": scope,
            "status": "NOT_STARTED",
            "conclusion": "NOT_RUN",
            "history": [],
            "professional_acceptance": "NOT_ASSERTED",
            "note": "Record the synthetic engagement's facts and scope judgments. Completion of "
            "this training task does not certify source interpretation or an actual deployment.",
        }
        for gate in gates.values()
    ]


def ism_catalog(repository: Path) -> dict:
    """Read the exact publisher non-classified profile; no automatic CCF equivalence.

    OSCAL input is parsed as data. External profile imports, URLs and references
    are never fetched during a user request. The original already resolved
    publisher profile supplies applicability; a learner must still tailor scope.
    """
    path = repository / "enterprise/generated/audit-suite/source-documents" / (ISM_SHA256 + ".json")
    if not path.is_file() or path.is_symlink():
        raise DomainError(
            "The verified ISM source profile is not installed", code="BLOCKED_SOURCE_OR_LICENSE"
        )
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != ISM_SHA256:
        raise DomainError("ISM source hash mismatch", code="SOURCE_INTEGRITY")
    catalog = json.loads(data)["catalog"]
    if catalog["metadata"]["version"] != ISM_VERSION:
        raise DomainError("Unexpected ISM source edition")
    rows = []

    def visit(node: dict, ancestry: list[str]) -> None:
        for control in node.get("controls", []):
            statements = [
                p["prose"]
                for p in control.get("parts", [])
                if p.get("name") == "statement" and p.get("prose")
            ]
            rows.append(
                {
                    "id": control["id"],
                    "title": control["title"],
                    "kind": control.get("class"),
                    "statement": "\n".join(statements),
                    "source_path": ancestry,
                    "framework": "IRAP",
                    "version": ISM_VERSION,
                    "applicability": "NON_CLASSIFIED",
                    "mapping_status": "UNMAPPED_REQUIRES_SCOPED_REVIEW",
                }
            )
            visit(control, ancestry + [control["id"]])
        for group in node.get("groups", []):
            visit(group, ancestry + [group.get("title", "")])

    visit(catalog, [])
    if len({r["id"] for r in rows}) != len(rows) or not rows:
        raise DomainError("ISM profile contains missing or duplicate requirement identities")
    return {
        "program": "IRAP",
        "version": ISM_VERSION,
        "classification": "NON_CLASSIFIED",
        "source_sha256": ISM_SHA256,
        "requirements": rows,
        "license": "CC-BY-4.0",
        "attribution": "Australian Signals Directorate, © Commonwealth of Australia 2026",
        "source_url": "https://www.cyber.gov.au/ism/oscal/v2026.09.4",
        "assessment_claim": "TRAINING_SCOPE_NOT_ASD_CERTIFICATION",
    }


def ism_tasks(scope: dict, repository: Path) -> list[dict]:
    """Create distinct requirement work, preserving explicit unaccepted mappings."""
    if "IRAP" not in scope["programs"]:
        return []
    pack = ism_catalog(repository)
    requirements = {r["id"]: r for r in pack["requirements"]}
    selected = scope.get("ism_requirement_ids", [])
    if (
        not isinstance(selected, list)
        or not selected
        or any(not isinstance(r, str) or r not in requirements for r in selected)
        or len(set(selected)) != len(selected)
    ):
        raise DomainError("Select distinct requirements from the installed ISM profile")
    if scope.get("ism_classification") != "NON_CLASSIFIED":
        raise DomainError("The installed training profile covers non-classified systems only")
    for field in ("ism_system_description", "ism_tailoring_rationale"):
        if not isinstance(scope.get(field), str) or not scope[field].strip():
            raise DomainError("IRAP scope requires " + field.replace("_", " "))
    result = []
    for req_id in selected:
        requirement = requirements[req_id]
        for boundary in scope["boundaries"]:
            result.append(
                {
                    "id": f"TASK-IRAP-{req_id}-{boundary}",
                    "kind": "PROGRAM_REQUIREMENT",
                    "boundary_id": boundary,
                    "title": requirement["title"],
                    "requirement_ids": [req_id],
                    "frameworks": ["IRAP"],
                    "statement": requirement["statement"],
                    "source_version": ISM_VERSION,
                    "source_sha256": ISM_SHA256,
                    "source_url": pack["source_url"],
                    "attribution": pack["attribution"],
                    "license": pack["license"],
                    "mapping_status": "UNMAPPED_REQUIRES_SCOPED_REVIEW",
                    "status": "NOT_STARTED",
                    "conclusion": "NOT_RUN",
                    "note": "",
                    "history": [],
                    "test": "Determine applicability to the stated system; identify implementation "
                    "and observable support, evaluate the selected ISM requirement, and record "
                    "the conclusion and any residual limitation. Shared CCF work is supporting "
                    "evidence only until its applicability is assessed.",
                }
            )
    return result


def build(repository: Path, source_root: Path, destination: Path) -> dict:
    native = compile_registry(repository)
    selections = {
        "baseline": [],
        "ISO27001": ["ISO27001"],
        "ISO42001": ["ISO42001"],
        "C5": ["C5"],
        "combined": ["ISO27001", "ISO42001", "C5"],
    }
    compiled = {name: plan(native, source_root, targets) for name, targets in selections.items()}
    result = {
        "version": 1,
        "native_digest": digest(native),
        "selections": compiled,
        "authority": "SOURCE_VERIFIED_CANDIDATE_DUTIES_NOT_PROFESSIONAL_ACCEPTANCE",
    }
    result["digest"] = digest(result)
    return private_json(destination, result)
