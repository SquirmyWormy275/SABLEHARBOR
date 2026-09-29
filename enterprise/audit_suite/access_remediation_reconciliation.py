"""Selected local removal-record consistency, without review closure or assurance."""

from .portfolio_explanation import NATIVE
from .store import DomainError

PARENT = {
    "population_ref_id": "review_population",
    "decisions_ref_id": "review_decisions",
    "reconciliation_ref_id": "review_reconciliation",
    "application_ref_id": "application",
    "hr_ref_id": "hr",
}
ATTEMPT = {
    "resolver_ref_id": "permission_resolver",
    "execution_ref_id": "execution_attempts",
    "state_ref_id": "entitlement_state",
    "verification_ref_id": "validation_probes",
}
QUALIFICATION = "LOCAL_ACCESS_REMEDIATION_CONTINUATION_NOT_CANON_EMPLOYMENT_OR_DEPLOYMENT"


def require(value, message):
    if not value:
        raise DomainError(message)


def checksum(value):
    return (
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    )


def names(value, label):
    require(
        isinstance(value, list)
        and len(value) <= 64
        and all(isinstance(x, str) and x for x in value)
        and len(value) == len(set(value)),
        "Distinct bounded " + label + " required",
    )
    return value


def native_pin(value):
    require(
        isinstance(value, dict)
        and all(isinstance(value.get(k), str) and value[k] for k in NATIVE[:4])
        and type(value.get("version")) is int
        and value["version"] > 0
        and checksum(value.get("sha256")),
        "Exact typed native source pin required",
    )
    return tuple(value[k] for k in NATIVE)


def analyze(contracts, sources, bodies, scope):
    """Observe already-authorized immutable captures; this function reads no stores.

    The surrounding report must recheck scope, revision, registry and source grants.
    Missing raw source metadata prevents independent selected-metadata recomputation.
    """
    # Lazy imports permit the report to import this optional helper without a cycle.
    from .iam_review_reconciliation import checks as review_checks
    from .source_dependency_reconciliation import utc
    from .temporal_workflow import bound

    require(isinstance(contracts, list) and len(contracts) <= 4, "At most4 removal contracts")
    require(isinstance(sources, list) and len(sources) <= 64, "At most64 selected sources")
    require(isinstance(bodies, dict), "Selected native bodies required")
    index = {}
    for source in sources:
        native_pin(source)
        require(
            all(
                isinstance(source.get(k), str) and source[k]
                for k in ("source_store_id", "source_system_alias", "event_at", "available_at")
            )
            and checksum(source.get("registry_sha256")),
            "Exact captured source routing and timestamps required",
        )
        require(
            isinstance(source.get("id"), str) and source["id"] and source["id"] not in index,
            "Distinct source IDs required",
        )
        index[source["id"]] = source
    output, used = [], set()
    for contract in contracts:
        require(
            isinstance(contract, dict)
            and set(contract)
            == {
                "parent",
                "producer_label_expected",
                "baseline_ref_id",
                "request_ref_id",
                "attempts",
                "followup_ref_ids",
            },
            "Exact removal reconciliation contract required",
        )
        parent = contract["parent"]
        require(
            isinstance(parent, dict) and set(parent) == set(PARENT), "Exact parent roles required"
        )
        label = contract["producer_label_expected"]
        require(isinstance(label, str) and label, "Explicit native producer label required")
        attempts = contract["attempts"]
        require(
            isinstance(attempts, list)
            and 1 <= len(attempts) <= 2
            and all(isinstance(a, dict) and set(a) == set(ATTEMPT) for a in attempts),
            "One or two exact selected attempts required",
        )
        followups = names(contract["followup_ref_ids"], "followup IDs")
        require(len(followups) <= 2, "At most2 followups")
        child_roles = [
            (contract["baseline_ref_id"], "entitlement_state"),
            (contract["request_ref_id"], "removal_requests"),
        ]
        child_roles += [(a[k], system) for a in attempts for k, system in ATTEMPT.items()]
        child_roles += [(sid, "remediation_followup") for sid in followups]
        ids = names([*parent.values(), *[sid for sid, _ in child_roles]], "contract source IDs")
        require(
            all(sid in index and isinstance(bodies.get(sid), dict) for sid in ids),
            "Explicit selected native sources required",
        )
        request_id = contract["request_ref_id"]
        require(request_id not in used, "Duplicate removal request contract")
        used.add(request_id)
        for key, system in PARENT.items():
            require(index[parent[key]]["system"] == system, "Parent native role mismatch")
        parent_observations = review_checks(
            [
                {
                    "population_ref_id": parent["population_ref_id"],
                    "decisions_ref_id": parent["decisions_ref_id"],
                    "reconciliation_ref_id": parent["reconciliation_ref_id"],
                    "application_ref_ids": [parent["application_ref_id"]],
                    "hr_ref_ids": [parent["hr_ref_id"]],
                }
            ],
            sources,
            bodies,
            scope,
        )[0]
        base = bodies[contract["baseline_ref_id"]]
        request = bodies[request_id]
        selected_parent = {native_pin(index[sid]) for sid in parent.values()}
        parent_ref = index[parent["population_ref_id"]]
        pop = bodies[parent["population_ref_id"]]
        recon = bodies[parent["reconciliation_ref_id"]]
        app = bodies[parent["application_ref_id"]]
        subject = request.get("subject_person_id")
        require(isinstance(subject, str) and subject, "Explicit subject required")
        decisions = bodies[parent["decisions_ref_id"]].get("decisions")
        require(isinstance(decisions, list), "Native decisions required")
        decision_matches = [
            d for d in decisions if isinstance(d, dict) and d.get("person_id") == subject
        ]
        require(len(decision_matches) == 1, "One selected native subject decision required")
        decision = decision_matches[0]
        removals = set(names(request.get("remove_rights"), "requested rights"))
        expected = set(names(request.get("authorized_rights"), "authorized rights"))
        require(removals and expected, "Explicit nonempty removal and remaining rights required")
        owner, reviewer = request.get("owner_id"), request.get("operating_reviewer_id")
        require(
            all(isinstance(v, str) and v for v in (owner, reviewer)),
            "Recorded operating actors required",
        )
        identity = index[request_id]
        expected_component = tuple(
            identity.get(k) for k in ("source_store_id", "company", "branch")
        )
        require(
            all(isinstance(v, str) and v for v in expected_component),
            "Routed continuation identity required",
        )
        require(
            expected_component
            != tuple(parent_ref.get(k) for k in ("source_store_id", "company", "branch")),
            "Separate continuation branch/component required",
        )
        require(
            identity["company"] == parent_ref["company"]
            and identity["branch"] != parent_ref["branch"],
            "Same native company and separate continuation branch required",
        )
        source_checks, lineage = [], []
        child_index = {}
        for sid, system in child_roles:
            ref, body = index[sid], bodies[sid]
            require(
                ref["system"] == system
                and tuple(ref.get(k) for k in ("source_store_id", "company", "branch"))
                == expected_component,
                "One routed native continuation with correct roles required",
            )
            require(
                body.get("classification") == QUALIFICATION
                and body.get("control_ids") == ["SH-IAM-007"]
                and body.get("boundary_id") in scope["boundaries"],
                "Qualified IAM007 native scope required",
            )
            start, stop = utc(body.get("period_start")), utc(body.get("period_end_exclusive"))
            require(start < stop, "Ordered native continuation interval required")
            event, available = utc(ref.get("event_at")), utc(ref.get("available_at"))
            require(
                start <= event < stop and event <= available,
                "Native continuation event/availability inconsistent",
            )
            links = body.get("source_records")
            require(
                isinstance(links, list) and len(links) == 5, "Five explicit upstream pins required"
            )
            pins = [native_pin(link) for link in links]
            require(len(set(pins)) == 5, "Distinct native parent references required")
            declared_pin = body.get("source_versions_sha256")
            require(checksum(declared_pin), "Typed declared selected metadata digest required")
            source_checks.append(
                {
                    "source_ref_id": sid,
                    "parent_native_pins_match": set(pins) == selected_parent,
                    "producer_label_matches": body.get("source_store_id") == label
                    and all(link.get("source_store_id") == label for link in links),
                    "parent_available_at_input": all(
                        utc(index[p]["available_at"]) <= start
                        and utc(index[p]["event_at"]) <= start
                        for p in parent.values()
                    ),
                    "parent_campaign_matches": body.get("parent_campaign") == pop.get("id")
                    and body.get("parent_branch") == parent_ref["branch"],
                    "subject_and_operating_actors_match": body.get("subject_person_id") == subject
                    and body.get("owner_id") == owner
                    and body.get("operating_reviewer_id") == reviewer,
                    "unresolved_population_retained": body.get("recorded_unresolved_population_ids")
                    == recon.get("missing_person_ids"),
                    "scope_interval_matches_request": (
                        body.get("period_start"),
                        body.get("period_end_exclusive"),
                        body.get("campaign_id"),
                    )
                    == (
                        request.get("period_start"),
                        request.get("period_end_exclusive"),
                        request.get("campaign_id"),
                    ),
                    "boundary_matches_request": body.get("boundary_id")
                    == request.get("boundary_id"),
                    "native_assurance_qualification": body.get("independent_assurance"),
                    "native_limits_match_generator_contract": (
                        body.get("independent_assurance") == "NOT_PERFORMED"
                        and body.get("population_completeness")
                        == "NOT_ESTABLISHED_OR_REMEDIATED_BY_THIS_SLICE"
                    ),
                    "native_population_qualification": body.get("population_completeness"),
                    "declared_selected_metadata_sha256": declared_pin,
                }
            )
            key = (ref["system"], ref["record"], ref["version"])
            require(key not in child_index, "Duplicate routed continuation native identity")
            child_index[key] = sid
        for sid, _ in child_roles:
            previous = bodies[sid].get("previous_events")
            require(
                isinstance(previous, list) and len(previous) <= 64,
                "Bounded previous-event links required",
            )
            seen = set()
            for link in previous:
                require(
                    isinstance(link, dict)
                    and set(link) == {"system", "record", "version", "sha256"},
                    "Exact previous-event reference required",
                )
                native_pin({"company": identity["company"], "branch": identity["branch"], **link})
                key = (link["system"], link["record"], link["version"])
                require(key not in seen, "Duplicate previous-event link")
                seen.add(key)
                target = child_index.get(key)
                lineage.append(
                    {
                        "source_ref_id": sid,
                        "target_ref_id": target,
                        "native_link": link,
                        "status": "MISSING_SELECTED_SUPPORT"
                        if target is None
                        else "EXACT_MATCH"
                        if index[target]["sha256"] == link["sha256"]
                        else "PIN_DIFFERS",
                        "available_before_dependent_event": None
                        if target is None
                        else utc(index[target]["available_at"]) <= utc(index[sid]["event_at"]),
                        "self_reference": target == sid,
                    }
                )
        observations = []
        prior_state = contract["baseline_ref_id"]
        for number, attempt in enumerate(attempts, 1):
            resolver_id, execution_id, state_id, probe_id = [attempt[k] for k in ATTEMPT]
            resolver, execution, state, probe = [
                bodies[sid] for sid in (resolver_id, execution_id, state_id, probe_id)
            ]
            before = set(names(bodies[prior_state].get("rights"), "prior state rights"))
            mapping = resolver.get("mapping")
            require(
                isinstance(mapping, dict)
                and len(mapping) <= 32
                and all(
                    isinstance(k, str) and k and isinstance(v, str) and v
                    for k, v in mapping.items()
                ),
                "Typed bounded local resolver mapping required",
            )
            mapping_authorized = all(k == v and k in removals for k, v in mapping.items())
            unresolved = removals - set(mapping)
            predicted = before - removals if mapping_authorized and not unresolved else before
            after = set(names(state.get("rights"), "recorded state rights"))
            probes = probe.get("removed_permission_probes")
            require(
                isinstance(probes, dict)
                and all(isinstance(k, str) and v in ("ALLOW", "DENY") for k, v in probes.items()),
                "Typed local permission probes required",
            )
            observations.append(
                {
                    "attempt": number,
                    "source_ref_ids": attempt,
                    "mapping_within_requested_authority": mapping_authorized,
                    "expected_unresolved_permissions": sorted(unresolved),
                    "predicted_local_after_rights": sorted(predicted),
                    "recorded_after_rights": sorted(after),
                    "state_matches_local_transition": after == predicted,
                    "execution_before_matches_prior_state": set(
                        names(execution.get("before_rights"), "execution before rights")
                    )
                    == before,
                    "execution_after_matches_state": set(
                        names(execution.get("after_rights"), "execution after rights")
                    )
                    == after,
                    "execution_removed_matches_state_difference": set(
                        names(execution.get("removed_rights"), "removed rights")
                    )
                    == before - after,
                    "execution_unresolved_matches_mapping": set(
                        names(execution.get("unresolved_permissions"), "unresolved rights")
                    )
                    == unresolved,
                    "operating_actors_match_recorded_roles": execution.get("performed_by") == owner
                    and probe.get("performed_by") == reviewer,
                    "recorded_operating_actors_distinct": owner != reviewer,
                    "probe_observation_matches_state": set(
                        names(probe.get("observed_rights"), "probe observed rights")
                    )
                    == after,
                    "probe_expectation_matches_request": set(
                        names(probe.get("expected_rights"), "probe expected rights")
                    )
                    == expected,
                    "probe_differences_match_state": set(
                        names(probe.get("excess_rights"), "probe excess rights")
                    )
                    == after - expected
                    and set(names(probe.get("missing_authorized_rights"), "probe missing rights"))
                    == expected - after,
                    "permission_probe_results_match_state": probes
                    == {r: "ALLOW" if r in after else "DENY" for r in sorted(removals)},
                    "causal_availability_matches": all(
                        utc(index[left]["available_at"]) <= utc(index[right]["event_at"])
                        for left, right in (
                            (request_id, resolver_id),
                            (resolver_id, execution_id),
                            (prior_state, execution_id),
                            (execution_id, state_id),
                            (state_id, probe_id),
                        )
                    ),
                    "execution_status_recorded": execution.get("status"),
                    "execution_status_matches_mapping": execution.get("status")
                    == (
                        "UNRESOLVED_PERMISSION_MAPPING"
                        if unresolved
                        else "APPLIED_OR_ALREADY_ABSENT"
                    )
                    and mapping_authorized,
                    "state_status_matches_execution": state.get("execution_status")
                    == execution.get("status"),
                    "external_permission_execution": (
                        "NOT_ESTABLISHED_BY_LOCAL_RECORD_RECONCILIATION"
                    ),
                }
            )
            prior_state = state_id
        audit_start = utc(bound(scope["period_start"], timezone=scope.get("timezone", "UTC")))
        audit_end = utc(
            bound(scope["period_end"], inclusive_end=True, timezone=scope.get("timezone", "UTC"))
        )
        output.append(
            {
                "request_ref_id": request_id,
                "control_id": "SH-IAM-007",
                "parent_review": parent_observations,
                "source_checks": source_checks,
                "lineage": lineage,
                "attempts": observations,
                "baseline_matches_selected_application": set(
                    names(base.get("rights"), "baseline rights")
                )
                == set(names(app.get("rights"), "application rights")),
                "request_subject_matches_selected_application": subject == app.get("person_id"),
                "request_matches_selected_decision": set(
                    names(decision.get("remove_rights"), "decision removals")
                )
                == removals
                and set(names(decision.get("authorized_rights"), "decision authorized rights"))
                == expected
                and decision.get("decision") == "REMOVE_EXCESS"
                and decision.get("removal_confirmation") == "NOT_YET_PERFORMED",
                "request_actor_matches_recorded_owner": request.get("requested_by") == owner
                and decision.get("decision_by") == owner,
                "declared_metadata_digests_consistent": len(
                    {r["declared_selected_metadata_sha256"] for r in source_checks}
                )
                == 1,
                "metadata_verification": "NOT_RECOMPUTABLE_FROM_RETAINED_FIELDS",
                "continuation_within_audit_period": audit_start
                <= utc(request["period_start"])
                < utc(request["period_end_exclusive"])
                <= audit_end,
                "recorded_unresolved_population_ids": recon.get("missing_person_ids"),
                "whole_review_closure": "NOT_ESTABLISHED",
                "population_acceptance": "NOT_PERFORMED",
                "control_effectiveness": "NOT_ASSESSED",
                "professional_assurance": "NOT_PERFORMED",
                "coherent_operating_year": "NOT_ESTABLISHED",
            }
        )
    return output
