"""Mechanical IAM007 native-record reconciliation over explicitly selected originals."""

from .operating_source_bridge import encoded, sha
from .source_dependency_reconciliation import require, utc
from .temporal_workflow import bound


def strings(value, label):
    require(
        isinstance(value, list)
        and all(isinstance(x, str) and x for x in value)
        and len(value) == len(set(value)),
        "Unique typed " + label + " required",
    )
    return value


def pin(record, version, checksum):
    require(
        isinstance(record, str)
        and bool(record)
        and type(version) is int
        and version > 0
        and isinstance(checksum, str)
        and len(checksum) == 64
        and all(c in "0123456789abcdef" for c in checksum),
        "Exact typed native record pin required",
    )
    return record, version, checksum


def checks(contracts, sources, bodies, scope):
    require(isinstance(contracts, list) and len(contracts) <= 8, "At most 8 IAM review contracts")
    index = {r["id"]: r for r in sources}
    output, used = [], set()
    for contract in contracts:
        require(
            isinstance(contract, dict)
            and set(contract)
            == {
                "population_ref_id",
                "decisions_ref_id",
                "reconciliation_ref_id",
                "application_ref_ids",
                "hr_ref_ids",
            },
            "Exact IAM review contract required",
        )
        ids = [
            contract[k] for k in ("population_ref_id", "decisions_ref_id", "reconciliation_ref_id")
        ]
        strings(ids, "review source IDs")
        require(
            all(k in index for k in ids) and ids[0] not in used,
            "Selected distinct review triple required",
        )
        used.add(ids[0])
        app_ids = strings(contract["application_ref_ids"], "application source IDs")
        hr_ids = strings(contract["hr_ref_ids"], "HR source IDs")
        require(
            len(app_ids) + len(hr_ids) <= 64 and all(k in index for k in app_ids + hr_ids),
            "Bounded explicitly selected support required",
        )
        pop_ref, decision_ref, recon_ref = [index[k] for k in ids]
        pop, decisions, reconciliation = [bodies[k] for k in ids]
        for ref, body, system in zip(
            (pop_ref, decision_ref, recon_ref),
            (pop, decisions, reconciliation),
            ("review_population", "review_decisions", "review_reconciliation"),
            strict=True,
        ):
            require(
                ref["system"] == system
                and body.get("control_id") == "SH-IAM-007"
                and all(ref[k] == pop_ref[k] for k in ("source_store_id", "company", "branch")),
                "Same routed IAM007 quarter sources required",
            )
            require(
                body.get("period_start") == pop.get("period_start")
                and body.get("period_end_exclusive") == pop.get("period_end_exclusive"),
                "Native quarter intervals differ",
            )
            require(
                body.get("boundary_id", "corporate") in scope["boundaries"]
                and body.get("boundary_id", "corporate") == pop.get("boundary_id", "corporate"),
                "Native boundary outside scope",
            )
        start, cutoff = utc(pop.get("period_start")), utc(pop.get("period_end_exclusive"))
        require(
            utc(bound(scope["period_start"], timezone=scope.get("timezone", "UTC")))
            <= start
            < cutoff
            <= utc(
                bound(
                    scope["period_end"], inclusive_end=True, timezone=scope.get("timezone", "UTC")
                )
            ),
            "IAM quarter outside audit scope",
        )
        query = pop.get("query")
        require(
            isinstance(query, dict)
            and query.get("system") == "application"
            and utc(query.get("as_of_exclusive")) == cutoff,
            "Exact exclusive application cutoff required",
        )
        for ref in (pop_ref, decision_ref, recon_ref):
            require(
                utc(ref["available_at"]) >= cutoff,
                "Review source available before its declared cutoff",
            )
        for selected_ids, system in ((app_ids, "application"), (hr_ids, "hr")):
            for sid in selected_ids:
                ref = index[sid]
                require(
                    ref["system"] == system
                    and all(ref[k] == pop_ref[k] for k in ("source_store_id", "company", "branch")),
                    "Support source outside review component/branch/system",
                )
        members = pop.get("members")
        require(isinstance(members, list) and len(members) <= 2000, "Bounded member list required")
        pin("membership", 1, pop.get("membership_sha256"))
        member_index, member_observations = {}, []
        for member in members:
            require(
                isinstance(member, dict)
                and isinstance(member.get("person_id"), str)
                and member["person_id"],
                "Typed population member required",
            )
            key = (
                member["person_id"],
                *pin(member.get("record"), member.get("version"), member.get("sha256")),
            )
            require(
                key not in member_index and not any(k[0] == key[0] for k in member_index),
                "Duplicate member identity/person",
            )
            rights = strings(member.get("rights"), "member rights")
            member_index[key] = member
            matches = [
                index[k]
                for k in app_ids
                if index[k]["record"] == key[1] and index[k]["version"] == key[2]
            ]
            status, selected_ids = "MISSING_SELECTED_SUPPORT", [r["id"] for r in matches]
            details = {}
            if len(matches) == 1:
                target = matches[0]
                body = bodies[target["id"]]
                status = "EXACT_PIN" if target["sha256"] == key[3] else "DIGEST_MISMATCH"
                available = utc(target["available_at"]) < cutoff and (
                    target.get("event_at") is None or utc(target["event_at"]) < cutoff
                )
                native_rights = strings(body.get("rights"), "native application rights")
                details = {
                    "source_before_exclusive_cutoff": available,
                    "person_matches": body.get("person_id") == key[0],
                    "rights_array_equal": native_rights == rights,
                    "rights_set_equal": set(native_rights) == set(rights),
                    "native_rights": native_rights,
                    "member_rights": rights,
                    "cause_matches": body.get("cause_id") == member.get("cause_id"),
                }
            elif len(matches) > 1:
                status = "AMBIGUOUS_SELECTED_SUPPORT"
            member_observations.append(
                {
                    "person_id": key[0],
                    "record": key[1],
                    "version": key[2],
                    "sha256": key[3],
                    "source_status": status,
                    "selected_source_ids": selected_ids,
                    **details,
                }
            )
        decision_rows = decisions.get("decisions")
        require(
            isinstance(decision_rows, list) and len(decision_rows) <= 2000,
            "Bounded decision list required",
        )
        decision_checks, seen = [], set()
        for decision in decision_rows:
            require(
                isinstance(decision, dict)
                and isinstance(decision.get("person_id"), str)
                and decision["person_id"],
                "Typed decision person required",
            )
            key = (
                decision["person_id"],
                *pin(
                    decision.get("source_record"),
                    decision.get("source_version"),
                    decision.get("source_sha256"),
                ),
            )
            require(key not in seen, "Duplicate decision identity")
            seen.add(key)
            observed = strings(decision.get("observed_rights"), "observed rights")
            authorized = strings(decision.get("authorized_rights"), "recorded authorized rights")
            removal = strings(decision.get("remove_rights"), "recorded removal rights")
            member = member_index.get(key)
            excess = sorted(set(observed) - set(authorized))
            decision_checks.append(
                {
                    "person_id": key[0],
                    "source_record": key[1],
                    "source_version": key[2],
                    "source_sha256": key[3],
                    "member_match": "EXACT_MEMBER" if member else "NO_EXACT_MEMBER",
                    "observed_rights": observed,
                    "rights_array_equal": observed == member["rights"] if member else None,
                    "rights_set_equal": set(observed) == set(member["rights"]) if member else None,
                    "recorded_authorized_rights": authorized,
                    "recomputed_excess_over_recorded_authorization": excess,
                    "recorded_remove_rights": removal,
                    "removal_set_matches_arithmetic": set(removal) == set(excess),
                    "recorded_decision": decision.get("decision"),
                    "recorded_removal_confirmation": decision.get("removal_confirmation"),
                    "removal_execution": "NOT_VERIFIED",
                    "authorization_validity": "NOT_ASSESSED",
                }
            )
        references = reconciliation.get("hr_sources")
        require(
            isinstance(references, list) and len(references) <= 2000,
            "Bounded HR reference list required",
        )
        hr_observations, hr_people, hr_seen = [], set(), set()
        for reference in references:
            require(isinstance(reference, dict), "Typed HR reference required")
            key = pin(reference.get("record"), reference.get("version"), reference.get("sha256"))
            require(key not in hr_seen, "Duplicate HR reference")
            hr_seen.add(key)
            matches = [
                index[k]
                for k in hr_ids
                if index[k]["record"] == key[0] and index[k]["version"] == key[1]
            ]
            status = "MISSING_SELECTED_SUPPORT"
            person = None
            if len(matches) == 1:
                target = matches[0]
                person = bodies[target["id"]].get("person_id")
                require(isinstance(person, str) and person, "Typed HR source person required")
                if target["sha256"] != key[2]:
                    status = "DIGEST_MISMATCH"
                elif utc(target["available_at"]) >= cutoff or (
                    target.get("event_at") is not None and utc(target["event_at"]) >= cutoff
                ):
                    status = "NOT_BEFORE_EXCLUSIVE_CUTOFF"
                else:
                    status = "EXACT_SELECTED_HR_REFERENCE"
                    hr_people.add(person)
            elif len(matches) > 1:
                status = "AMBIGUOUS_SELECTED_SUPPORT"
            hr_observations.append(
                {
                    "record": key[0],
                    "version": key[1],
                    "sha256": key[2],
                    "status": status,
                    "person_id": person,
                    "selected_source_ids": [r["id"] for r in matches],
                }
            )
        recorded_hr = strings(reconciliation.get("hr_visible_person_ids"), "recorded HR people")
        recorded_export = strings(reconciliation.get("export_person_ids"), "recorded export people")
        recorded_missing = strings(
            reconciliation.get("missing_person_ids"), "recorded missing people"
        )
        exported = {k[0] for k in member_index}
        complete = all(r["status"] == "EXACT_SELECTED_HR_REFERENCE" for r in hr_observations)
        for body in (decisions, reconciliation):
            pin("population", 1, body.get("population_sha256"))
        output.append(
            {
                "population_ref_id": ids[0],
                "decisions_ref_id": ids[1],
                "reconciliation_ref_id": ids[2],
                "review_event_timing": [
                    {
                        "source_ref_id": ref["id"],
                        "event_at": ref.get("event_at"),
                        "available_at": ref["available_at"],
                        "status": (
                            "UNDATED"
                            if ref.get("event_at") is None
                            else "EVENT_BEFORE_DECLARED_CUTOFF"
                            if utc(ref["event_at"]) < cutoff
                            else "AT_OR_AFTER_DECLARED_CUTOFF"
                        ),
                        "execution_inference": "NOT_MADE_FROM_AVAILABILITY",
                    }
                    for ref in (pop_ref, decision_ref, recon_ref)
                ],
                "membership_hash_matches": sha(encoded(members)) == pop["membership_sha256"],
                "decision_population_hash_matches": decisions["population_sha256"]
                == pop_ref["sha256"],
                "reconciliation_population_hash_matches": reconciliation["population_sha256"]
                == pop_ref["sha256"],
                "members": member_observations,
                "decisions": decision_checks,
                "members_without_exact_decision": [list(k) for k in member_index if k not in seen],
                "hr_references": hr_observations,
                "hr_resolution": "ALL_LISTED_HR_REFERENCES_RESOLVED"
                if complete
                else "PARTIAL_SELECTED_SUPPORT",
                "recorded_hr_people": recorded_hr,
                "recorded_export_people": recorded_export,
                "recorded_missing_people": recorded_missing,
                "member_people": sorted(exported),
                "recorded_export_matches_members": set(recorded_export) == exported,
                "recorded_list_difference": sorted(set(recorded_hr) - set(recorded_export)),
                "recorded_missing_matches_recorded_list_difference": set(recorded_missing)
                == set(recorded_hr) - set(recorded_export),
                "selected_hr_people": sorted(hr_people),
                "selected_hr_matches_recorded_hr": set(recorded_hr) == hr_people
                if complete
                else None,
                "selected_hr_minus_members": sorted(hr_people - exported) if complete else None,
                "recorded_missing_matches_selected_hr_difference": set(recorded_missing)
                == hr_people - exported
                if complete
                else None,
                "population_completeness": "NOT_ESTABLISHED",
                "control_effectiveness": "NOT_ASSESSED",
                "limitation": (
                    "Resolution covers listed selected references only; no enterprise census, "
                    "latest-version completeness, valid authorization or performed removal "
                    "is inferred."
                ),
            }
        )
    return output
