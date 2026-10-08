"""Pure, private causal episode authoring from exact admitted native originals.

Procedure metadata defines questions. Native bytes define literal witnesses.
Neither stored queries, auditor outcomes nor private witness aliases are run or
accepted as authority. Binding and actual audited visibility remain root-owned.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime

IDENTITY = ("company", "branch", "system", "record", "version")
BRANCHES = {"CLEAN": "HARBOR-OPERATIONS-A", "MESSY": "HARBOR-OPERATIONS-B"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Explicit dated instant required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timezone required")
    return parsed


def pointer(document, path):
    value = document
    if path:
        if not path.startswith("/"):
            raise ValueError("Exact JSON pointer required")
        for part in path[1:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def walk(document, path=""):
    if isinstance(document, dict):
        for key, value in sorted(document.items()):
            if key != "previous_native_content":
                part = key.replace("~", "~0").replace("/", "~1")
                yield from walk(value, path + "/" + part)
    elif isinstance(document, list):
        if not document:
            yield path, []
        for number, value in enumerate(document):
            yield from walk(value, path + "/" + str(number))
    else:
        yield path, document


def row_identity(row):
    if type(row.get("version")) is not int or row["version"] < 1:
        raise ValueError("Strict positive native version required")
    if any(not isinstance(row.get(k), str) or not row[k] for k in IDENTITY[:-1]):
        raise ValueError("Exact native coordinates required")
    return tuple(row[k] for k in IDENTITY)


class Originals:
    def __init__(self, rows, admitted_routes):
        self.rows, self.documents, self.ids, self.facts = {}, {}, {}, {}
        self.routes = {tuple(r[k] for k in IDENTITY[:3]) for r in admitted_routes}
        self.unadmitted = []
        for row in rows:
            key = row_identity(row)
            if key in self.rows or not isinstance(row.get("content"), bytes):
                raise ValueError("Distinct original bytes required")
            if hashlib.sha256(row["content"]).hexdigest() != row["sha256"]:
                raise ValueError("Original content pin changed")
            if key[:3] not in self.routes:
                self.unadmitted.append({k: row[k] for k in (*IDENTITY, "sha256")})
                continue
            for field in ("event_at", "available_at", "imported_at"):
                if row[field] is not None:
                    instant(row[field])
            if row["event_at"] is not None and instant(row["event_at"]) > instant(
                row["available_at"]
            ):
                raise ValueError("Original chronology invalid")
            sid = "SRC-" + digest([*key, row["sha256"]])[:32]
            self.rows[key], self.ids[sid] = row, key
            try:
                self.documents[sid] = json.loads(row["content"])
            except (ValueError, UnicodeError):
                pass

    def source_id(self, row):
        return "SRC-" + digest([*row_identity(row), row["sha256"]])[:32]

    def source(self, sid):
        row = self.rows[self.ids[sid]]

        def classification(value):
            if value is None:
                return "UNKNOWN_NATIVE_TIME"
            year = instant(value).year
            return "POST_PERIOD" if year > 2027 else "ANTECEDENT" if year < 2027 else "IN_PERIOD"

        event_period = classification(row["event_at"])
        publication_period = classification(row["available_at"])
        return {
            **{k: row[k] for k in (*IDENTITY, "sha256", "event_at", "available_at", "imported_at")},
            "id": sid,
            "discovery_class": (
                "ADMITTED_EXACT_PHYSICAL_ROLE_HISTORICAL_AND_CURRENT_VERSION_REQUIRES"
                "_DATE_AND_SCOPED_GRANT"
            ),
            "audited_actor_visibility": (
                "UNBOUND_ROOT_ACTUAL_CLOCK_ACL_AND_SOURCE_CHECKPOINT_RECHECK_REQUIRED"
            ),
            "period_classification": "POST_PERIOD"
            if publication_period == "POST_PERIOD" or event_period == "POST_PERIOD"
            else event_period,
            "native_event_period_classification": event_period,
            "publication_period_classification": publication_period,
            "publication_date_is_not_the_operating_occurrence_date": True,
            "parse_status": "PARSED_ORIGINAL"
            if sid in self.documents
            else "UNPARSED_ORIGINAL_NO_CONTENT_PREDICATE",
        }

    def fact(self, sid, path):
        value = pointer(self.documents[sid], path)
        fid = "FACT-" + digest([sid, path])[:32]
        self.facts[fid] = {
            "id": fid,
            "source_id": sid,
            "locator": path,
            "value": value,
            "typed_value_sha256": digest(value),
            "attribution": "LITERAL_COMPANY_ORIGINAL_NOT_AUDITOR_RESULT",
        }
        return fid

    def selected(self, branch, systems, records=None):
        systems = set(systems)
        return sorted(
            (
                self.source_id(r)
                for r in self.rows.values()
                if r["branch"] == branch
                and r["system"] in systems
                and (records is None or r["record"] in records)
            ),
            key=lambda s: self.ids[s],
        )

    def exact_reference(self, reference, branch, *, before=None, systems=None):
        try:
            key = row_identity(reference)
        except (KeyError, ValueError):
            return None, "UNTYPED_ORIGINAL_DECLARATION_NOT_AUTHORITY"
        row = self.rows.get(key)
        if reference["branch"] != branch:
            return None, "FOREIGN_BRANCH_NOT_AUTHORITY"
        if row is None or row["sha256"] != reference.get("sha256"):
            return None, "MISSING_UNADMITTED_OR_ORIGINAL_NAMESPACE_ONLY"
        if systems is not None and row["system"] not in systems:
            return None, "WRONG_NATIVE_PHYSICAL_ROLE"
        if any(
            k in reference and reference[k] != row[k]
            for k in ("event_at", "available_at", "imported_at")
        ):
            return None, "ORIGINAL_CLOCK_MISMATCH"
        if before is not None and (
            instant(row["available_at"]) > instant(before)
            or row["event_at"] is None
            or instant(row["event_at"]) > instant(before)
        ):
            return None, "ORIGINAL_UNAVAILABLE_AT_OCCURRENCE"
        return self.source_id(row), "EXACT_AVAILABLE_NATIVE_ORIGINAL"


def relevant_paths(document, fields):
    wanted = set(fields)

    def visit(value, path=""):
        if isinstance(value, dict):
            for key, child in sorted(value.items()):
                if key in {"previous_native_content", "original_source_witness", "provenance"}:
                    continue
                child_path = path + "/" + key.replace("~", "~0").replace("/", "~1")
                if key in wanted:
                    # Keep a full typed array/object once. Exploding every member
                    # into duplicate cards would obscure the actual decision.
                    yield child_path
                else:
                    yield from visit(child, child_path)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                yield from visit(child, path + "/" + str(i))

    yield from visit(document)


def source_scene(originals, spec, branch):
    selected = originals.selected(branch, spec["systems"], spec.get("records"))
    if not selected:
        raise ValueError("Scene requires admitted physical witnesses: " + spec["id"])
    facts, statuses = [], []
    for sid in selected:
        doc = originals.documents.get(sid)
        if doc is None:
            continue
        for path in relevant_paths(doc, spec["fields"]):
            fid = originals.fact(sid, path)
            facts.append(fid)
            # The Key card quotes exact native business outcomes; complete other
            # witnesses remain in the typed companion, not thousands of cards.
            if path.rsplit("/", 1)[-1] in spec["headline_fields"] and not isinstance(
                originals.facts[fid]["value"], (dict, list)
            ):
                f = originals.facts[fid]
                row = originals.source(sid)
                statuses.append(
                    {
                        "source_id": sid,
                        "fact_id": fid,
                        "sentence": (
                            f"{row['system']}:{row['record']} v{row['version']} "
                            f"({row['available_at']}) records {path}={canonical(f['value'])}."
                        ),
                    }
                )
        # Compound detail facts stay whole above, while scalar decision/status
        # locators provide compact exact sentences instead of an opaque blob.
        for path, value in walk(doc):
            if path.rsplit("/", 1)[-1] not in spec["headline_fields"]:
                continue
            if isinstance(value, (dict, list)) or any(
                part in path
                for part in (
                    "/source",
                    "/previous",
                    "/upstream",
                    "/dependencies",
                    "/reference",
                    "/provenance",
                    "/original_source_witness",
                )
            ):
                continue
            fid = originals.fact(sid, path)
            facts.append(fid)
            if not any(item["fact_id"] == fid for item in statuses):
                row = originals.source(sid)
                statuses.append(
                    {
                        "source_id": sid,
                        "fact_id": fid,
                        "sentence": (
                            f"{row['system']}:{row['record']} v{row['version']} "
                            f"({row['available_at']}) records {path}={canonical(value)}."
                        ),
                    }
                )
        if isinstance(doc, dict) and isinstance(doc.get("detail"), dict):
            for path, _value in walk(doc["detail"], "/detail"):
                if any(
                    part in path
                    for part in (
                        "/source",
                        "/previous",
                        "/upstream",
                        "/dependencies",
                        "/reference",
                        "/provenance",
                        "/original_source_witness",
                    )
                ):
                    continue
                facts.append(originals.fact(sid, path))
    if not facts:
        raise ValueError("Scene has no exact literal attribute witnesses: " + spec["id"])
    histories = defaultdict(list)
    for sid in selected:
        histories[originals.ids[sid][:-1]].append(sid)
    changed = []
    for ids in histories.values():
        ids.sort(key=lambda s: originals.source(s)["version"])
        for prior, later in zip(ids, ids[1:], strict=False):
            if prior not in originals.documents or later not in originals.documents:
                continue
            old = {
                p: pointer(originals.documents[prior], p)
                for p in relevant_paths(originals.documents[prior], spec["fields"])
            }
            new = {
                p: pointer(originals.documents[later], p)
                for p in relevant_paths(originals.documents[later], spec["fields"])
            }
            for p in sorted(old.keys() | new.keys()):
                if canonical(old.get(p)) != canonical(new.get(p)) or (p in old) != (p in new):
                    changed.append(
                        {
                            "prior_source_id": prior,
                            "later_source_id": later,
                            "locator": p,
                            "prior_exists": p in old,
                            "later_exists": p in new,
                            "prior_value": old.get(p),
                            "later_value": new.get(p),
                            "later_does_not_replace_earlier_tested_state": True,
                        }
                    )
    present = {originals.source(s)["system"] for s in selected}
    return {
        "id": spec["id"] + "-" + branch[-1],
        "title": spec["title"],
        "cause_identity": spec["cause_identity"],
        "control_ids": spec["control_ids"],
        "source_ids": selected,
        "native_fact_ids": sorted(set(facts)),
        "selected_physical_roles": sorted(present),
        "requested_roles_without_admitted_original": sorted(set(spec["systems"]) - present),
        "scope_task_ids": spec.get("scope_task_ids", []),
        "factual_sentences": statuses,
        "dated_history_changes": changed,
        "interpretation": spec["interpretation"],
        "unknowns": spec["unknowns"],
        "source_body_is_management_declaration_not_auditor_conclusion": True,
        "actual_binding_or_grading": False,
    }


# These are independently authored witness questions, not conclusions inherited
# from a control or metadata. Matching a role retains documentary context only.
PHASE_ROLES = {
    "TOD": {
        "authority",
        "catalogue",
        "definition",
        "scope",
        "matrix",
        "inventory",
        "plan",
        "programme",
        "procedure",
        "baseline",
        "request",
        "criteria",
        "classification",
        "purpose",
        "agreement",
        "contract",
        "policy",
        "approval",
        "delegation",
        "motion",
        "charter",
        "code",
        "rule",
        "configuration",
        "desired",
        "requirement",
        "hr",
        "registration",
        "integrity",
        "intake",
        "review",
        "docket",
        "zoning",
        "assignment",
    },
    "IMPLEMENTATION": {
        "application",
        "operation",
        "attempt",
        "release",
        "flow",
        "receipt",
        "review",
        "decision",
        "action",
        "test",
        "probe",
        "recovery",
        "result",
        "finding",
        "exception",
        "response",
        "dispatch",
        "completion",
        "attestation",
        "delivery",
        "transfer",
        "gate",
        "state",
        "intake",
        "triage",
        "assessment",
        "notification",
        "screening",
        "reconciliation",
        "remediation",
        "approval",
        "badge",
        "visitor",
        "monitor",
        "build",
        "configuration",
        "export",
        "job",
        "registration",
        "integrity",
        "retrieval",
        "assignment",
        "delegation",
        "document",
        "docket",
    },
    "TOE": {
        "period",
        "calendar",
        "schedule",
        "population",
        "denominator",
        "inventory",
        "roster",
        "register",
        "reconciliation",
        "monitoring",
        "due",
        "review",
        "followup",
        "checkpoint",
        "ledger",
        "export",
        "exception",
        "finding",
        "overdue",
        "intake",
        "requirement",
        "build",
        "test",
        "configuration",
        "assignment",
        "notification",
        "release",
        "delivery",
        "registration",
        "gate",
    },
}
PHASE_QUESTIONS = {
    "TOD": (
        "Which original establishes the effective rule, exact actor delegatio"
        "n and exception design before this decision? A status/result is exec"
        "ution context, not proof of effective design."
    ),
    "IMPLEMENTATION": (
        "Which exact actor and object/version was acted on, what gate/input w"
        "as available then, and what failed or changed later? Compare actual "
        "action and retained exception; do not substitute a later approval."
    ),
    "TOE": (
        "Which dated due/trigger inventory contains every relevant occurrence"
        ", which were actually examined on time, and which remain missing/lat"
        "e/untested? A final reconciled count does not erase an earlier gap."
    ),
    "ADDITIONAL_DUTY": (
        "Which original independently addresses this exact extra condition, a"
        "nd what triggered event, authority or alternative remains unproved? "
        "Context for the base control cannot grant this requirement credit."
    ),
    "SCOPE_DEPENDENCY": (
        "Which exact entity/site/data/edition dependency is established by a "
        "dated native declaration, and which owner or qualified interpretatio"
        "n remains open? Do not assign a control or acceptance from a source "
        "statement."
    ),
}


def _terms(value):
    return {
        w
        for w in re.findall(r"[a-z0-9]+", value.lower())
        if len(w) > 3
        and w
        not in {
            "actual",
            "original",
            "selected",
            "source",
            "record",
            "records",
            "inspect",
            "control",
            "trace",
            "review",
            "require",
            "required",
            "against",
            "before",
            "after",
            "separate",
            "complete",
            "scope",
            "scoped",
            "without",
            "rather",
            "retain",
            "company",
            "check",
            "including",
            "condition",
            "conditions",
            "their",
            "these",
            "this",
            "each",
            "with",
            "that",
            "from",
            "full",
            "exact",
            "independent",
            "test",
            "tests",
            "proposed",
        }
    }


def task_facet(originals, task, scenes):
    control = task["control_id"]
    relevant = [
        s
        for s in scenes
        if (control is not None and control in s["control_ids"])
        or task["task_id"] in s.get("scope_task_ids", [])
    ]
    if not relevant:
        raise ValueError("Concrete decision chapter required for " + task["task_id"])
    meta, contract = task["metadata"], task["contract"]
    kind = meta["kind"]
    instruction = meta.get("authored_instruction") or contract["performed"]
    candidates = sorted({sid for scene in relevant for sid in scene["source_ids"]})
    native_facts = sorted({fid for scene in relevant for fid in scene["native_fact_ids"]})
    clause = (
        task["task_id"].split("CHECK-HIPAA:", 1)[-1] if "CHECK-HIPAA:" in task["task_id"] else None
    )
    exact_clause_sources = []
    if clause:
        for sid in candidates:
            doc = originals.documents.get(sid)
            if isinstance(doc, dict):
                provision = (
                    doc.get("detail", {}).get("provision", {})
                    if isinstance(doc.get("detail"), dict)
                    else {}
                )
                if isinstance(provision, dict) and provision.get("id") == "45-CFR-" + clause:
                    exact_clause_sources.append(sid)
        if not exact_clause_sources and clause.startswith(("160.3", "160.4", "160.5")):
            # Actual company playbook declares case context and recheck at
            # trigger. It is not a fabricated enforcement/hearing occurrence.
            exact_clause_sources = [
                sid
                for sid in candidates
                if originals.source(sid)["system"] == "legint.regulatory_response_playbook"
            ]
    if kind == "SCOPE_DEPENDENCY":
        selected = candidates
    elif exact_clause_sources:
        selected = sorted(exact_clause_sources)
    elif kind == "ADDITIONAL_DUTY":
        selected = candidates
    else:
        words = PHASE_ROLES.get(kind)
        if words is None:
            words = _terms(instruction)
        selected = [
            sid
            for sid in candidates
            if any(w in originals.source(sid)["system"].split(".")[-1] for w in words)
        ]
    # No silent fallback to an unrelated document. Missing phase-specific roles
    # stay unresolved; the chapter itself supplies only contextual explanation.
    selected_set = set(selected)
    fact_ids = [fid for fid in native_facts if originals.facts[fid]["source_id"] in selected_set]
    if kind == "ADDITIONAL_DUTY" and not exact_clause_sources:
        terms = _terms(instruction + " " + meta.get("required_checks", ""))
        fact_ids = [
            fid
            for fid in fact_ids
            if any(
                w
                in (
                    originals.facts[fid]["locator"] + " " + canonical(originals.facts[fid]["value"])
                ).lower()
                for w in terms
            )
        ]
    if clause and exact_clause_sources:
        for sid in exact_clause_sources:
            doc = originals.documents[sid]
            for key in (
                "detail",
                "real_hipaa_applicability",
                "2027_legal_text_verified",
                "source_complete",
                "hearing_or_penalty_case",
                "penalty_amounts",
                "2027_primary_authority_status",
                "procedure",
                "scope",
                "reference_checked_as_of",
            ):
                if key in doc:
                    fact_ids.append(originals.fact(sid, "/" + key))
    fact_ids = sorted(set(fact_ids))
    gap_fact_ids = []
    if not fact_ids:
        for fid in native_facts:
            f = originals.facts[fid]
            leaf = f["locator"].rsplit("/", 1)[-1]
            value = f["value"]
            if leaf in {
                "scope_limit",
                "unmodeled_scope",
                "qualification_evidence_status",
                "backup_evidence_status",
                "source_complete",
                "full_enterprise_population_complete",
                "actual_legal_applicability",
                "real_hipaa_applicability",
                "physical_channel_scope",
                "evaluated_effectiveness",
                "applicability_status",
                "qualified_review_status",
                "reserved_authority",
            }:
                gap_fact_ids.append(fid)
            elif isinstance(value, str) and (
                "NOT_ESTABLISHED" in value or "UNDETERMINED" in value or "NOT_OBTAINED" in value
            ):
                gap_fact_ids.append(fid)
        # These are actual source-declared support limitations, never invented
        # operating occurrences or a claim that a particular event did not occur.
    witness_fact_ids = sorted(set(fact_ids + gap_fact_ids))
    selected = sorted({originals.facts[f]["source_id"] for f in witness_fact_ids})
    witness_index = [
        {
            "source_id": sid,
            "native_role": originals.source(sid)["system"],
            "record": originals.source(sid)["record"],
            "version": originals.source(sid)["version"],
            "event_at": originals.source(sid)["event_at"],
            "available_at": originals.source(sid)["available_at"],
            "period_classification": originals.source(sid)["period_classification"],
            "literal_fact_ids": [
                fid for fid in witness_fact_ids if originals.facts[fid]["source_id"] == sid
            ],
        }
        for sid in selected
    ]
    return {
        "task_id": task["task_id"],
        "control_id": control,
        "kind": kind,
        "batch": task["batch"],
        "cause_episode_ids": [s["id"] for s in relevant],
        "exact_expected_attribute": instruction,
        "control_specific_procedure": meta.get("authored_procedure", contract["performed"]),
        "required_checks": meta.get("required_checks", contract["performed"]),
        "distinct_witness_question": PHASE_QUESTIONS[kind],
        "task_clause": clause,
        "native_role_source_ids": selected,
        "native_witnesses": witness_index,
        "native_fact_ids": fact_ids,
        "source_declared_gap_fact_ids": gap_fact_ids,
        "gap_witness_is_not_proof_of_event_nonoccurrence": True,
        "source_witness_disposition": "DATED_LITERAL_WITNESSES_ONLY_FULL_ATTRIBUTE_NOT_ASSUMED"
        if fact_ids
        else "NO_EXACT_ATTRIBUTE_WITNESS_ESTABLISHED_CONTEXT_ONLY",
        "contextual_chapter_sources_are_not_task_population": True,
        "specific_unsupported_attributes": contract["unperformed"],
        "acceptable_alternatives": [
            (
                "Obtain independently the named physical roles and versions below, in"
                "cluding their prior authority and unavailable originals; perform thi"
                "s exact question: "
            )
            + instruction,
            (
                "Preserve this task as a specifically bounded limitation and pursue i"
                "ts missing population/authority/trigger inputs: "
            )
            + contract["unperformed"],
        ],
        "audited_actor_visibility": "UNBOUND_REQUIRES_CURRENT_COMPANY_CLOCK_ACL_RECHECK",
        "professional_qualified_owner_or_grade_acceptance": "NOT_ASSERTED",
    }
