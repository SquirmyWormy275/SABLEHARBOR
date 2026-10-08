"""Additive native operating followthrough over independent business declarations.

Existing person/account denominators, quarterly reviews, corrected changes and
commissioning records are inputs, never regenerated. No audit Engine or Key operation is invoked.
This is trusted-local fictional business operation, not enterprise certification.
"""

import fcntl
import math
import os
import re
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

from . import company_backup_runtime as backup
from . import company_backup_use_probe as use_probe
from . import company_policy_delivery_runtime as policy
from .company_access_remediation_activity import LocalEntitlements
from .company_change_activity import evaluate
from .company_store import CompanyStoreError, _id, _time
from .inference import _json as decode
from .operating_source_bridge import encoded, sha
from .organization import snapshot

DECLARATION = "SH_COMPANY_NATIVE_OPERATING_DEPTH_DECLARATION_V1"
SYSTEM = "operating_depth_followthrough"
QUALIFICATION = "FICTIONAL_DECLARED_NATIVE_OPERATIONS_NOT_ENTERPRISE_OR_PROFESSIONAL_ACCEPTANCE"
PIN = {"company", "branch", "system", "record", "version", "sha256"}
MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 4096


def require(condition, message):
    if not condition:
        raise CompanyStoreError(message)


def keys(value, expected):
    require(type(value) is dict and set(value) == set(expected.split()), "Exact fields required")


def names(value, maximum=512):
    require(type(value) is list and len(value) <= maximum, "Bounded identity list required")
    for item in value:
        _id(item)
    require(len(value) == len(set(value)), "Duplicate identity")
    return value


def exact_pin(value):
    require(type(value) is dict and set(value) == PIN, "Exact native pin required")
    for key in ("company", "branch", "system", "record"):
        _id(value[key])
    require(type(value["version"]) is int and value["version"] > 0, "Positive native version")
    checksum = value["sha256"]
    require(
        type(checksum) is str
        and len(checksum) == 64
        and all(c in "0123456789abcdef" for c in checksum),
        "Exact native SHA256 required",
    )
    return value


def pin(row):
    return {key: row[key] for key in PIN}


def physical_role(reference, role, prefix):
    require(
        reference["system"] in {role, prefix + "." + role},
        "Exact admitted physical native role required",
    )


def selected(db, reference, at, scope=None):
    exact_pin(reference)
    if scope:
        require(
            (reference["company"], reference["branch"]) == scope,
            "Foreign native business scope",
        )
    row = db.execute(
        "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
        "AND record=? AND version=?",
        tuple(reference[k] for k in ("company", "branch", "system", "record", "version")),
    ).fetchone()
    require(row is not None, "Exact native original unavailable")
    require(
        type(row["content"]) is bytes
        and 0 < len(row["content"]) <= MAX_BYTES
        and sha(row["content"]) == row["sha256"] == reference["sha256"],
        "Native original bytes differ",
    )
    require(
        row["event_at"] is not None
        and _time(row["event_at"]) <= at
        and _time(row["available_at"]) <= at,
        "Native input not yet available or undated",
    )
    try:
        body = decode(row["content"].decode("utf-8"))
    except (ValueError, UnicodeError) as error:
        raise CompanyStoreError("Typed native object required") from error
    require(type(body) is dict, "Native object required")
    return dict(row), body


def _reference(value, *, native_row=None):
    """Known six/eight/nine-field pointers preserve identity and exact native clocks."""
    require(
        type(value) is dict
        and set(value)
        in (
            PIN,
            PIN | {"event_at", "available_at"},
            PIN | {"event_at", "available_at", "imported_at"},
        ),
        "Typed literal native reference required",
    )
    result = {key: value[key] for key in PIN}
    exact_pin(result)
    if set(value) != PIN:
        require(
            type(native_row) is dict and pin(native_row) == result,
            "Exact selected native clock header required",
        )
        for field in set(value) - PIN:
            require(
                type(value[field]) is str
                and type(native_row.get(field)) is str
                and _time(value[field]) == _time(native_row[field]),
                "Embedded native reference clock differs",
            )
    return result


@contextmanager
def writer(store):
    path = store.path.parent / ".operating-depth.lock"
    require(not path.is_symlink(), "Writer lock alias")
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        require(info.st_nlink == 1 and info.st_mode & 0o777 == 0o600, "Private writer lock")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def _due_offset(value):
    """One explicit day or second offset; cadence remains exact whole days."""
    require(type(value) is dict, "Exact calendar fields required")
    present = set(value) & {"due_offset_days", "due_offset_seconds"}
    require(len(present) == 1, "Exactly one day or second due offset required")
    key = next(iter(present))
    cadence = value.get("cadence_days")
    require(type(cadence) is int and 1 <= cadence <= 366, "Typed bounded cadence required")
    offset = value[key]
    maximum = 366 if key == "due_offset_days" else 366 * 86400
    require(type(offset) is int and 1 <= offset <= maximum, "Typed bounded cadence required")
    seconds = offset * 86400 if key == "due_offset_days" else offset
    require(seconds <= cadence * 86400, "Due exceeds cadence")
    return key, timedelta(seconds=seconds)


def _declaration(db, reference, at):
    row, body = selected(db, reference, at)
    require(
        row["system"] == "operating_depth_definition" and row["record"] == body.get("runtime_id"),
        "Exact registered operating-depth declaration role and runtime identity required",
    )
    return _validated_definition(db, row, body, at)


def _validated_definition(db, row, body, at):
    offset_key, _ = _due_offset(body)
    keys(
        body,
        "schema runtime_id company branch declared_at recorded_at "
        "period_start period_end_exclusive "
        f"inventory_scope business_inventory_ref cadence_days {offset_key} items exclusions "
        "retained_period_refs local_basis",
    )
    require(body["schema"] == DECLARATION, "Operating-depth declaration schema differs")
    require(
        body["inventory_scope"]
        == "EXPLICIT_COMPANY_BUSINESS_INVENTORY_NOT_SELECTED_AUDIT_ARTIFACTS",
        "Independent business inventory basis required",
    )
    _id(body["runtime_id"])
    scope = (row["company"], row["branch"])
    require(scope == (body["company"], body["branch"]), "Declaration routing differs")
    for key in ("declared_at", "recorded_at", "period_start", "period_end_exclusive"):
        require(_time(body[key]) == body[key], "Normalized declaration clocks required")
    require(
        body["declared_at"] <= body["period_start"] < body["period_end_exclusive"]
        and body["declared_at"] <= body["recorded_at"] == _time(row["event_at"]),
        "Prospective calendar with truthful later native binding clock required",
    )
    require(
        type(body["local_basis"]) is str and 10 <= len(body["local_basis"]) <= 2000,
        "Explicit source boundary required",
    )
    require(
        exact_pin(body["business_inventory_ref"])["system"] == "business_inventory",
        "Exact admitted physical business inventory role required",
    )
    _, inventory = selected(db, body["business_inventory_ref"], body["declared_at"], scope)
    calendar = {
        key: body[key]
        for key in (
            "declared_at",
            "period_start",
            "period_end_exclusive",
            "cadence_days",
            offset_key,
            "items",
            "exclusions",
        )
    }
    require(
        encoded(inventory.get("operating_depth_calendar")) == encoded(calendar),
        "Calendar must be exact independently native declared business schedule",
    )
    require(
        type(inventory.get("systems")) is list and 1 <= len(inventory["systems"]) <= 128,
        "Independent native system inventory required",
    )
    systems = [item.get("system") for item in inventory["systems"] if type(item) is dict]
    names(systems, 128)
    require(len(systems) == len(inventory["systems"]), "Typed inventory system rows required")
    require(type(body["items"]) is list and 1 <= len(body["items"]) <= 128, "Bounded items")
    ids = []
    for item in body["items"]:
        keys(item, "id system_id kind operating_from operating_to_exclusive commissioning_ref")
        ids.append(_id(item["id"]))
        require(item["system_id"] in systems, "Item outside independent business inventory")
        require(item["kind"] in {"IAM", "POLICY", "RETRY", "RESTORE"}, "Unsupported item kind")
        start, stop = _time(item["operating_from"]), _time(item["operating_to_exclusive"])
        require(
            start == item["operating_from"]
            and stop == item["operating_to_exclusive"]
            and start < stop,
            "Exact operating window required",
        )
        if item["kind"] == "RESTORE":
            require(
                exact_pin(item["commissioning_ref"])["system"]
                in {"site_release", "transition.site_release"},
                "Exact admitted physical commissioning role required",
            )
            release, document = selected(db, item["commissioning_ref"], at, scope)
            require(
                document.get("fictional_in_universe_operating_release") is True
                and document.get("status")
                in {
                    "OPERATING_PRIMARY_SIMULATED",
                    "OPERATING_RECOVERY_SIMULATED",
                    "OPERATING_RECOVERY_WITH_OPEN_EXCEPTION_SIMULATED",
                }
                and _time(release["event_at"]) == start,
                "Exact existing commissioning release and window required",
            )
        else:
            require(item["commissioning_ref"] is None, "Commissioning applies only to restore")
    names(ids, 128)
    require(
        type(body["exclusions"]) is list and len(body["exclusions"]) <= 128,
        "Bounded explicit exclusions required",
    )
    excluded = []
    for exclusion in body["exclusions"]:
        keys(exclusion, "system_id reason source_ref")
        excluded.append(exclusion["system_id"])
        require(
            exclusion["system_id"] in systems
            and type(exclusion["reason"]) is str
            and 10 <= len(exclusion["reason"]) <= 2000,
            "Exact supported exclusion required",
        )
        selected(db, exclusion["source_ref"], body["declared_at"], scope)
    names(excluded, 128)
    covered = {item["system_id"] for item in body["items"]}
    require(
        not covered & set(excluded) and covered | set(excluded) == set(systems),
        "Every independent system needs operation scope or explicit exclusion",
    )
    require(
        type(body["retained_period_refs"]) is list and len(body["retained_period_refs"]) <= 64,
        "Bounded retained period joins",
    )
    seen = set()
    for ref in body["retained_period_refs"]:
        record, document = selected(db, ref, at, scope)
        identity = tuple(ref[k] for k in ("system", "record", "version"))
        require(
            identity not in seen and document.get("schema") == "SH_COMPANY_PERSON_ACCESS_RECORD_V1",
            "Exact existing person-period joins",
        )
        seen.add(identity)
        require(record["record"].startswith("2027-"), "Existing 2027 period identity required")
    return row, body


def register_declaration(
    store,
    *,
    repository,
    business_inventory_pin,
    retained_period_refs,
    runtime_id,
    actor_id,
    recorded_at,
    command_id,
    expected_version=0,
):
    """Normal native registration of an already independent business calendar.

    The inventory/calendar must already exist and be available by its declared
    clock. No due slot, account population, review decision or earlier operation
    is inferred from audit selections. A newly recorded binding is not earlier
    discoverability or a cure of a past deadline.
    """
    at = _time(recorded_at)
    _id(runtime_id)
    _id(actor_id)
    require(type(expected_version) is int and expected_version >= 0, "Exact declaration CAS")
    with writer(store), store._db() as db:
        db.execute("BEGIN")
        inventory_row, inventory = selected(db, business_inventory_pin, at)
        calendar = inventory.get("operating_depth_calendar")
        require(type(calendar) is dict, "Existing independently native calendar required")
        offset_key, _ = _due_offset(calendar)
        keys(
            calendar,
            "declared_at period_start period_end_exclusive cadence_days "
            f"{offset_key} items exclusions",
        )
        owner = db.execute(
            "SELECT owner FROM systems WHERE company=? AND branch=? AND system=?",
            (inventory_row["company"], inventory_row["branch"], inventory_row["system"]),
        ).fetchone()
        require(owner is not None and owner[0] == actor_id, "Exact independent inventory custodian")
        definition = dict(
            schema=DECLARATION,
            runtime_id=runtime_id,
            company=inventory_row["company"],
            branch=inventory_row["branch"],
            recorded_at=at,
            inventory_scope="EXPLICIT_COMPANY_BUSINESS_INVENTORY_NOT_SELECTED_AUDIT_ARTIFACTS",
            business_inventory_ref=business_inventory_pin,
            retained_period_refs=retained_period_refs,
            local_basis=inventory.get("whole_estate_claim"),
            **calendar,
        )
        _validated_definition(db, {**inventory_row, "event_at": at}, definition, at)
        require(
            len(snapshot(repository, as_of=calendar["declared_at"][:10])["canonical_people"]) == 52,
            "Canonical person count differs",
        )
        # Consume the original joins without asserting a new denominator.
        person_period_joins(store, references=retained_period_refs, as_of=at)
        db.commit()
        store.register_system(
            inventory_row["company"],
            inventory_row["branch"],
            "operating_depth_definition",
            actor_id,
        )
        return store.append_version(
            inventory_row["company"],
            inventory_row["branch"],
            "operating_depth_definition",
            runtime_id,
            expected_version=expected_version,
            command_id=command_id,
            event_at=at,
            available_at=at,
            content=encoded(definition),
            provenance={
                "source_reference": business_inventory_pin["record"],
                "independent_business_inventory_pin": business_inventory_pin,
                "new_registration_not_earlier_discoverability": True,
                "name": runtime_id + ".json",
                "content_type": "application/json",
            },
        )


def declare(store, *, repository, declaration_pin, as_of):
    """Admit an existing independent native declaration; write no roster or due history."""
    at = _time(as_of)
    with store._db() as db:
        db.execute("BEGIN")
        row, body = _declaration(db, declaration_pin, at)
    org = snapshot(repository, as_of=body["declared_at"][:10])
    require(len(org["canonical_people"]) == 52, "Canonical person count differs")
    return {
        "declaration_pin": pin(row),
        "runtime_id": body["runtime_id"],
        "canonical_person_count": 52,
        "schedule": schedule(body),
        "retained_person_period_joins": person_period_joins(
            store, references=body["retained_period_refs"], as_of=at
        ),
        "qualification": QUALIFICATION,
        "enterprise_completeness_established": False,
    }


def person_period_joins(store, *, references, as_of):
    """Consume existing monthly/quarterly originals, without authoring replacements.

    Production 2027 closure requires twelve denominator/reconciliation pairs and
    four population/decision/followup triples. A bounded subset remains a subset.
    This checks registered-source joins; it does not infer an unnamed SaaS estate.
    """
    at = _time(as_of)
    require(type(references) is list and len(references) <= 64, "Bounded exact period references")
    roles = (
        "denominator_snapshot",
        "monthly_reconciliation",
        "periodic_review_population",
        "periodic_review_decisions",
        "review_followup",
    )
    accepted_roles = {name: name for name in roles} | {
        "person-access-history." + name: name for name in roles
    }
    rows, scope, total = {}, None, 0
    with store._db() as db:
        db.execute("BEGIN")
        for ref in references:
            exact_pin(ref)
            require(ref["system"] in accepted_roles, "Unknown physical person-period role")
            role = accepted_roles[ref["system"]]
            row, body = selected(db, ref, at, scope)
            scope = (row["company"], row["branch"])
            total += len(row["content"])
            require(
                total <= MAX_BYTES and body.get("schema") == "SH_COMPANY_PERSON_ACCESS_RECORD_V1",
                "Bounded typed existing person-period originals",
            )
            key = (role, row["record"])
            require(key not in rows, "Ambiguous period original/version")
            rows[key] = (ref, row, body)
    missing, monthly, quarterly = [], [], []
    for month in range(1, 13):
        record = f"2027-{month:02}"
        pair = [(role, record) for role in roles[:2]]
        missing.extend(
            [
                dict(role=role, record=identity)
                for role, identity in pair
                if (role, identity) not in rows
            ]
        )
        if not all(key in rows for key in pair):
            continue
        census_ref, census_row, census = rows[pair[0]]
        recon_ref, _, recon = rows[pair[1]]
        cutoff = datetime(
            2028 if month == 12 else 2027,
            1 if month == 12 else month + 1,
            1,
            tzinfo=datetime.fromisoformat(at).tzinfo,
        ).isoformat(timespec="microseconds")
        require(
            _time(census["cutoff_exclusive"]) == cutoff == _time(census_row["event_at"]),
            "Monthly source cutoff was moved",
        )
        names(census.get("registered_subject_ids"), 512)
        require(
            type(census.get("accounts")) is list and len(census["accounts"]) <= 1024,
            "Typed monthly account denominator",
        )
        require(
            _reference(recon.get("denominator"), native_row=census_row) == census_ref
            and recon.get("expected_subject_ids") == census["registered_subject_ids"]
            and recon.get("account_population_sha256") == sha(encoded(census["accounts"])),
            "Monthly native denominator/reconciliation join differs",
        )
        monthly.append(
            dict(
                record=record,
                denominator_pin=census_ref,
                reconciliation_pin=recon_ref,
                registered_subject_count=len(census["registered_subject_ids"]),
                account_count=len(census["accounts"]),
                missing_account_subject_ids=names(recon.get("missing_account_subject_ids"), 512),
                unmatched_review_subject_ids=names(recon.get("unmatched_review_subject_ids"), 512),
            )
        )
    for quarter in range(1, 5):
        record = f"2027-Q{quarter}"
        triple = [(role, record) for role in roles[2:]]
        missing.extend(
            [
                dict(role=role, record=identity)
                for role, identity in triple
                if (role, identity) not in rows
            ]
        )
        if not all(key in rows for key in triple):
            continue
        pop_ref, pop_row, pop = rows[triple[0]]
        dec_ref, dec_row, decisions = rows[triple[1]]
        follow_ref, follow_row, follow = rows[triple[2]]
        require(
            _reference(decisions.get("population"), native_row=pop_row) == pop_ref
            and _reference(follow.get("review"), native_row=dec_row) == dec_ref
            and pop.get("membership_sha256")
            == decisions.get("population_sha256")
            == follow.get("population_sha256")
            == sha(encoded(pop.get("members"))),
            "Quarter original population/decision/followup join differs",
        )
        monthly_key = ("denominator_snapshot", f"2027-{quarter * 3:02}")
        require(
            monthly_key in rows
            and _reference(pop.get("denominator"), native_row=rows[monthly_key][1])
            == rows[monthly_key][0],
            "Quarter requires its exact original monthly denominator",
        )
        require(
            type(pop.get("members")) is list and type(decisions.get("decisions")) is list,
            "Typed original quarterly members/decisions",
        )
        members = {m["subject_id"]: m for m in pop["members"] if type(m) is dict}
        require(len(members) == len(pop["members"]), "Duplicate quarterly member")
        names(list(members), 512)
        expected = []
        for subject, member in members.items():
            require(type(member.get("accounts")) is list, "Typed quarterly account entries")
            actual = sorted(
                {right for a in member["accounts"] for right in names(a["state"]["rights"], 32)}
            )
            removal = (
                ["billing-admin"] if {"billing-admin", "inventory-admin"} <= set(actual) else []
            )
            expected.append(
                dict(
                    subject_id=subject,
                    observed_rights=actual,
                    remove_rights=removal,
                    decision="REMOVAL_REQUESTED" if removal else "RETAIN_SCOPED_DUTIES",
                    removal_confirmation=None if removal else "NO_REMOVAL_REQUEST",
                )
            )
        missing_ids = names(decisions.get("missing_subject_ids"), 512)
        open_work = bool(missing_ids or any(d["remove_rights"] for d in expected))
        require(
            encoded(decisions["decisions"]) == encoded(expected)
            and decisions.get("review_status")
            == ("RECONCILIATION_OPEN" if open_work else "REGISTERED_SCOPE_REVIEW_RECORDED")
            and decisions.get("wider_estate_reviewed") is False
            and encoded(follow.get("removal_work"))
            == encoded([d for d in expected if d["remove_rights"]])
            and follow.get("person_mapping_work") == missing_ids
            and follow.get("status")
            == ("OPEN" if open_work else "NO_ACTION_REQUIRED_FOR_REGISTERED_SCOPE")
            and follow.get("historical_reviews_replaced") is False
            and _time(dec_row["event_at"]) <= _time(follow_row["event_at"]),
            "Original quarterly followup/status/decision scope differs",
        )
        quarterly.append(
            dict(
                record=record,
                population_pin=pop_ref,
                decisions_pin=dec_ref,
                followup_pin=follow_ref,
                missing_subject_ids=names(decisions.get("missing_subject_ids"), 512),
                removal_work=deepcopy(follow.get("removal_work")),
                original_followup_status=follow.get("status"),
            )
        )
    require(
        set(rows)
        <= {(role, f"2027-{m:02}") for role in roles[:2] for m in range(1, 13)}
        | {(role, f"2027-Q{q}") for role in roles[2:] for q in range(1, 5)},
        "Unexpected existing period identity",
    )
    return {
        "monthly": monthly,
        "quarterly": quarterly,
        "missing_original_joins": missing,
        "complete_registered_2027_period_join": not missing,
        "unnamed_other_estate": "NOT_ESTABLISHED_BY_REGISTERED_PERSON_SOURCE",
        "new_population_or_quarter_review_authored": False,
    }


def schedule(body):
    """Derive expected due slots from prospective cadence, not returned observations."""
    _, offset = _due_offset(body)
    start, stop = map(datetime.fromisoformat, (body["period_start"], body["period_end_exclusive"]))
    result = []
    ordinal = 0
    while start < stop:
        end = min(start + timedelta(days=body["cadence_days"]), stop)
        due = min(start + offset, end)
        for item in body["items"]:
            active = (
                datetime.fromisoformat(item["operating_from"])
                < due
                <= datetime.fromisoformat(item["operating_to_exclusive"])
            )
            result.append(
                {
                    "slot_id": f"{item['id']}:{ordinal}",
                    "item_id": item["id"],
                    "kind": item["kind"],
                    "window_start": start.isoformat(timespec="microseconds"),
                    "window_end_exclusive": end.isoformat(timespec="microseconds"),
                    "due_at": due.isoformat(timespec="microseconds"),
                    "expected": active,
                    "exclusion": None if active else "OUTSIDE_EXACT_NATIVE_OPERATING_WINDOW",
                }
            )
        require(len(result) <= 512, "Operating schedule exceeds bounded512 slots")
        ordinal += 1
        start = end
    return result


def _slot(db, declaration_pin, slot_id, at, kind):
    row, definition = _declaration(db, declaration_pin, at)
    slots = [slot for slot in schedule(definition) if slot["slot_id"] == slot_id]
    require(
        len(slots) == 1 and slots[0]["kind"] == kind and slots[0]["expected"],
        "Exact expected domain occurrence required",
    )
    slot = slots[0]
    require(slot["window_start"] <= at, "Operation precedes declared occurrence")
    item = next(item for item in definition["items"] if item["id"] == slot["item_id"])
    require(
        item["operating_from"] <= at < item["operating_to_exclusive"],
        "Operation outside exact native operating window",
    )
    return row, definition, slot


def _append(
    store, definition, declaration_row, slot, command_id, event_at, expected_version, observation
):
    body = {
        "schema": "SH_NATIVE_OPERATING_DEPTH_OBSERVATION_V1",
        "kind": slot["kind"],
        "declaration_pin": pin(declaration_row),
        "slot": slot,
        "recorded_at": event_at,
        "observation": observation,
        "qualification": QUALIFICATION,
        "professional_acceptance": "NOT_ASSERTED",
    }
    with store._db() as db:
        owner = db.execute(
            "SELECT owner FROM systems WHERE company=? AND branch=? AND system=?",
            (definition["company"], definition["branch"], declaration_row["system"]),
        ).fetchone()
    require(owner is not None, "Native declaration custodian missing")
    store.register_system(definition["company"], definition["branch"], SYSTEM, owner[0])
    return store.append_version(
        definition["company"],
        definition["branch"],
        SYSTEM,
        definition["runtime_id"] + ":" + slot["slot_id"],
        expected_version=expected_version,
        command_id=command_id,
        event_at=event_at,
        available_at=event_at,
        content=encoded(body),
        provenance={
            "source_reference": declaration_row["record"],
            "name": sha(
                encoded(
                    [
                        definition["company"],
                        definition["branch"],
                        SYSTEM,
                        definition["runtime_id"],
                        slot["slot_id"],
                    ]
                )
            )
            + ".json",
            "content_type": "application/json",
            "qualification": QUALIFICATION,
        },
    )


def access_followup(
    store,
    *,
    declaration_pin,
    slot_id,
    population_pin,
    decisions_pin,
    account_pins,
    actor_id,
    reviewer_id,
    permission_mapping,
    command_id,
    expected_version,
    event_at,
):
    """Execute ONLY removals requested by the exact existing quarterly review.

    Denominator and quarterly objects remain originals. Unsupported/unmapped
    subjects and missing mappings stay open. A retry carries actual prior state.
    """
    at = _time(event_at)
    _id(actor_id)
    _id(reviewer_id)
    require(actor_id != reviewer_id, "Distinct operating verifier required")
    require(type(expected_version) is int and expected_version >= 0, "Exact source CAS")
    require(
        type(account_pins) is list and 1 <= len(account_pins) <= 1024,
        "Bounded exact account originals required",
    )
    require(type(permission_mapping) is dict, "Typed permission mappings required")
    with writer(store), store._db() as db:
        db.execute("BEGIN")
        decl, definition, slot = _slot(db, declaration_pin, slot_id, at, "IAM")
        scope = (definition["company"], definition["branch"])
        retained = {encoded(ref) for ref in definition["retained_period_refs"]}
        require(
            encoded(population_pin) in retained and encoded(decisions_pin) in retained,
            "Quarterly originals not admitted by independent declaration",
        )
        pop_row, pop = selected(db, population_pin, at, scope)
        dec_row, decision = selected(db, decisions_pin, at, scope)
        physical_role(population_pin, "periodic_review_population", "person-access-history")
        physical_role(decisions_pin, "periodic_review_decisions", "person-access-history")
        match = re.fullmatch(r"2027-Q([1-4])", population_pin["record"])
        require(
            match is not None and decisions_pin["record"] == population_pin["record"],
            "Exact existing same quarterly record required",
        )
        quarter = int(match[1])
        start = _time(f"2027-{quarter * 3 - 2:02}-01T00:00:00+00:00")
        cutoff = _time(
            "2028-01-01T00:00:00+00:00"
            if quarter == 4
            else f"2027-{quarter * 3 + 1:02}-01T00:00:00+00:00"
        )
        require(
            _time(pop["period_start"]) == start and _time(pop["period_end_exclusive"]) == cutoff,
            "Existing quarter was truncated or moved",
        )
        require(
            pop.get("schema") == decision.get("schema") == "SH_COMPANY_PERSON_ACCESS_RECORD_V1",
            "Existing person-review format",
        )
        require(
            _reference(decision.get("population"), native_row=pop_row) == population_pin,
            "Decision references another exact population",
        )
        require(
            decision.get("reviewed_by") == reviewer_id and pop.get("exported_by") == actor_id,
            "Exact original review actors required",
        )
        require(
            decision.get("population_sha256")
            == pop.get("membership_sha256")
            == sha(encoded(pop.get("members"))),
            "Exact review membership digest",
        )
        require(
            _time(pop["period_end_exclusive"])
            <= _time(pop_row["event_at"])
            <= _time(dec_row["event_at"])
            <= at,
            "Review/followup chronology",
        )
        require(
            type(pop.get("members")) is list
            and len(pop["members"]) <= 512
            and type(decision.get("decisions")) is list,
            "Typed existing review membership",
        )
        required = []
        members = {}
        # Bounded fresh headers exist only inside this source read transaction.
        # The later account loop still verifies full bytes, state and physical role.
        account_headers = {}
        for reference in account_pins:
            row, _ = selected(db, reference, cutoff, scope)
            account_headers[encoded(reference)] = {
                key: row[key] for key in PIN | {"event_at", "available_at", "imported_at"}
            }
        for member in pop["members"]:
            require(
                type(member) is dict and type(member.get("accounts")) is list,
                "Typed retained account member",
            )
            subject = _id(member["subject_id"])
            require(subject not in members, "Duplicate subject in retained population")
            members[subject] = member
            for account in member["accounts"]:
                require(
                    type(account) is dict and set(account) == {"source", "state"},
                    "Exact retained native account entry",
                )
                source = account["source"]
                require(
                    type(source) is dict and PIN <= source.keys(),
                    "Typed retained native account reference required",
                )
                required.append(
                    _reference(source, native_row=account_headers.get(encoded(pin(source))))
                )
        require(
            len({encoded(p) for p in required}) == len(required)
            and {encoded(p) for p in required} == {encoded(p) for p in account_pins}
            and len(required) == len(account_pins),
            "Complete exact retained account set",
        )
        decisions = {d["subject_id"]: d for d in decision["decisions"] if type(d) is dict}
        require(
            len(decisions) == len(decision["decisions"]) and set(decisions) == set(members),
            "Exact decision membership required",
        )
        before = {}
        originals = {}
        total = 0
        for reference in account_pins:
            row, body = selected(db, reference, _time(pop["period_end_exclusive"]), scope)
            require(
                reference["system"]
                in {
                    prefix + role
                    for prefix in ("", "person-access-history.")
                    for role in (
                        "account_directory",
                        "account_application",
                        "account_local_account",
                        "account_remote_access",
                        "account_api_token",
                        "account_application_session",
                        "account_legacy_application",
                    )
                },
                "Exact known native account-state role",
            )
            require(_time(row["available_at"]) < cutoff, "Account source at exclusive cutoff")
            total += len(row["content"])
            require(total <= MAX_BYTES, "Bounded account payload exceeded")
            state = body.get("state")
            keys(
                state,
                "account_id subject_id channel rights active starts ends "
                "credential_epoch review_anchor",
            )
            require(
                type(state) is dict and type(state.get("active")) is bool,
                "Actual native local account state required",
            )
            subject, account = state.get("subject_id"), state.get("account_id")
            _id(account)
            require(subject in members and account not in before, "Exact unique subject account")
            embedded = [
                a
                for a in members[subject]["accounts"]
                if _reference(
                    a["source"], native_row=account_headers.get(encoded(pin(a["source"])))
                )
                == reference
            ]
            require(
                len(embedded) == 1 and encoded(embedded[0]["state"]) == encoded(state),
                "Population state differs from native original",
            )
            names(state.get("rights"), 32)
            require(
                type(state["credential_epoch"]) is int
                and state["credential_epoch"] > 0
                and state["channel"]
                in {
                    "directory",
                    "application",
                    "local_account",
                    "remote_access",
                    "api_token",
                    "application_session",
                    "legacy_application",
                },
                "Typed original account channel/credential edition",
            )
            require(state["active"] is True, "Retained active population contains inactive account")
            require(
                _time(state["starts"]) < _time(pop["period_end_exclusive"]) <= _time(state["ends"]),
                "Account outside exclusive review cutoff",
            )
            before[account] = deepcopy(state)
            originals[account] = reference
        record = definition["runtime_id"] + ":" + slot_id
        prior = db.execute(
            "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
            "AND record=? AND version=?",
            (*scope, SYSTEM, record, expected_version),
        ).fetchone()
        if expected_version:
            require(
                prior is not None and sha(prior["content"]) == prior["sha256"],
                "Exact prior followup state required",
            )
            old = decode(prior["content"].decode())
            require(
                old["declaration_pin"] == declaration_pin
                and old["kind"] == "IAM"
                and old["observation"]["population_pin"] == population_pin
                and old["observation"]["decisions_pin"] == decisions_pin
                and old["observation"]["original_accounts"] == originals,
                "Prior followup belongs to another review",
            )
            require(_time(prior["event_at"]) <= at, "Prior followup is later")
            before = old["observation"]["after_states"]
            require(
                type(before) is dict and set(before) == set(originals),
                "Prior account membership changed",
            )
            for account, state in before.items():
                native = next(
                    a["state"]
                    for member in members.values()
                    for a in member["accounts"]
                    if a["state"]["account_id"] == account
                )
                require(
                    encoded({k: v for k, v in state.items() if k != "rights"})
                    == encoded({k: v for k, v in native.items() if k != "rights"}),
                    "Prior followup changed identity/lifetime/channel",
                )
                names(state["rights"], 32)
                removed = set(native["rights"]) - set(state["rights"])
                require(
                    set(state["rights"]) <= set(native["rights"])
                    and removed <= set(decisions[state["subject_id"]]["remove_rights"]),
                    "Prior followup broadened state or removed unrequested rights",
                )
        require(set(permission_mapping) == set(before), "Exact complete account mapping keys")
        after, results = deepcopy(before), []
        for account, state in sorted(before.items()):
            d = decisions[state["subject_id"]]
            removals = names(d.get("remove_rights"), 32)
            observed = names(d.get("observed_rights"), 32)
            native_union = sorted(
                {r for a in members[state["subject_id"]]["accounts"] for r in a["state"]["rights"]}
            )
            require(
                observed == native_union and set(removals) <= set(observed),
                "Decision rights differ from native population",
            )
            requested = sorted(set(removals) & set(state["rights"]))
            mapping = permission_mapping[account]
            require(
                type(mapping) is dict
                and all(k == v and k in requested for k, v in mapping.items()),
                "Resolver redirects or broadens requested permissions",
            )
            if requested:
                local = LocalEntitlements(
                    state["subject_id"], actor_id, reviewer_id, state["rights"], requested
                )
                execution = local.execute(actor_id, state["subject_id"], requested, mapping)
                # Retest reads actual post-operation ACL, independently of status text.
                expected = sorted(set(state["rights"]) - set(requested))
                verification = {
                    "observed_rights": sorted(local.rights),
                    "expected_rights": expected,
                    "removed_permission_probes": {
                        r: "ALLOW" if r in local.rights else "DENY" for r in requested
                    },
                    "verified_by": reviewer_id,
                    "verification_basis": "LOCAL_RIGHT_SET_NOT_CREDENTIAL_OR_LIFETIME_PROBE",
                }
                after[account]["rights"] = sorted(local.rights)
            else:
                require(mapping == {}, "No unrequested removal mapping")
                execution = {
                    "status": "NO_REMAINING_REQUESTED_REMOVAL",
                    "unresolved_permissions": [],
                }
                verification = {
                    "observed_rights": state["rights"],
                    "expected_rights": state["rights"],
                    "removed_permission_probes": {},
                    "verified_by": reviewer_id,
                }
            results.append(
                {"account_id": account, "execution": execution, "verification": verification}
            )
        missing = names(decision.get("missing_subject_ids"), 512)
        unresolved = bool(missing or any(r["execution"]["unresolved_permissions"] for r in results))
        observation = {
            "population_pin": population_pin,
            "decisions_pin": decisions_pin,
            "original_accounts": originals,
            "before_states": before,
            "after_states": after,
            "results": results,
            "missing_subject_ids": missing,
            "performed_by": actor_id,
            "verified_by": reviewer_id,
            "status": "OPEN_UNRESOLVED_SCOPE_OR_PERMISSION"
            if unresolved
            else "REQUESTED_LOCAL_REMOVALS_VERIFIED",
            "all_rights_authorized": "NOT_ESTABLISHED_BY_REMOVAL_ONLY",
            "old_population_or_review_replaced": False,
        }
        # End the read transaction before normal append; the private writer lease remains held.
        db.commit()
        return _append(store, definition, decl, slot, command_id, at, expected_version, observation)


def retry_probe(
    store,
    *,
    declaration_pin,
    slot_id,
    configuration_pin,
    build_pin,
    test_pin,
    actor_id,
    command_id,
    event_at,
    expected_version=0,
):
    """Execute the existing local schema/combined-budget model over corrected originals."""
    at = _time(event_at)
    with writer(store), store._db() as db:
        db.execute("BEGIN")
        decl, definition, slot = _slot(db, declaration_pin, slot_id, at, "RETRY")
        scope = (definition["company"], definition["branch"])
        config_row, config = selected(db, configuration_pin, at, scope)
        build_row, build = selected(db, build_pin, at, scope)
        test_row, test = selected(db, test_pin, at, scope)
        for ref, role in (
            (configuration_pin, "configurations"),
            (build_pin, "builds"),
            (test_pin, "tests"),
        ):
            physical_role(ref, role, "change-history")
        owner = db.execute(
            "SELECT owner FROM systems WHERE company=? AND branch=? AND system=?",
            (*scope, configuration_pin["system"]),
        ).fetchone()
        require(
            owner is not None and owner[0] == actor_id, "Exact configuration custodian required"
        )
        require(
            config.get("configuration_sha256") == sha(encoded(config.get("configuration"))),
            "Exact existing configuration object digest required",
        )
        package = build.get("package")
        require(
            type(package) is dict
            and encoded(package.get("configuration")) == encoded(config["configuration"])
            and build.get("package_sha256") == sha(encoded(package)),
            "Build config differs",
        )
        for embedded, expected, original_row, dependent_row in (
            (build.get("source"), configuration_pin, config_row, build_row),
            (test.get("artifact"), build_pin, build_row, test_row),
        ):
            dependency_keys = {"system_id", "record_id", "version", "sha256", "available_at"}
            native_keys = dependency_keys | {"company_id", "branch_id", "event_at"}
            require(
                type(embedded) is dict
                and set(embedded) in (dependency_keys, native_keys)
                and (
                    set(embedded) == dependency_keys
                    or (
                        embedded["company_id"] == original_row["company"] == scope[0]
                        and embedded["branch_id"] == original_row["branch"] == scope[1]
                        and embedded["system_id"] == expected["system"]
                        and type(embedded["event_at"]) is str
                        and _time(embedded["event_at"]) == _time(original_row["event_at"])
                    )
                )
                and embedded["system_id"]
                in {expected["system"], expected["system"].removeprefix("change-history.")}
                and embedded.get("record_id") == expected["record"]
                and type(embedded.get("version")) is int
                and embedded["version"] == expected["version"]
                and embedded.get("sha256") == expected["sha256"]
                and _time(embedded["available_at"]) == _time(original_row["available_at"])
                and _time(original_row["available_at"]) <= _time(dependent_row["event_at"]),
                "Exact original dependency differs",
            )
        result = evaluate(config["configuration"])
        observation = {
            "configuration_pin": configuration_pin,
            "build_pin": build_pin,
            "original_test_pin": test_pin,
            "performed_by": _id(actor_id),
            "executed_scope": "LOCAL_POSITIVE_INTEGER_SCHEMA_AND_COMBINED_RETRY_LIMIT",
            "calculation": result,
            "status": "PASS_LOCAL_RETRY_CRITERION"
            if result["within_local_limit"]
            else "FAIL_LOCAL_RETRY_CRITERION",
            "security_privacy_pipeline_tests": "NOT_EXECUTED_BY_THIS_MODEL",
            "corrected_originals_replaced": False,
        }
        db.commit()
        return _append(store, definition, decl, slot, command_id, at, expected_version, observation)


def policy_binding(
    store,
    *,
    declaration_pin,
    slot_id,
    runtime_root,
    runtime_sha256,
    actor_id,
    command_id,
    event_at,
    expected_version=0,
):
    """Bind actual mailbox copy/read receipts; timestamp alone never becomes a receipt.

    Delivery and READ_RETURN use the existing policy runtime. Missing recipients,
    prior versions, lateness and lack of human acknowledgement remain explicit.
    """
    at = _time(event_at)
    with writer(store), store._db() as db:
        db.execute("BEGIN")
        decl, definition, slot = _slot(db, declaration_pin, slot_id, at, "POLICY")
        cfg = policy._config(Path(runtime_root), runtime_sha256)
        require(
            (cfg["plan"]["company"], cfg["plan"]["branch"])
            == (definition["company"], definition["branch"]),
            "Foreign policy runtime",
        )
        require(cfg["plan"]["owner_id"] == actor_id, "Exact policy owner required")
        _, inventory = selected(db, definition["business_inventory_ref"], definition["declared_at"])
        item = next(item for item in definition["items"] if item["id"] == slot["item_id"])
        registered = next(s for s in inventory["systems"] if s["system"] == item["system_id"])
        require(
            registered.get("recipients") == cfg["plan"]["recipients"]
            and registered.get("document_sha256") is not None,
            "Policy recipient denominator must match independent business inventory",
        )
        view = policy.inspect_at(runtime_root, expected_runtime_sha256=runtime_sha256, as_of=at)
        document = view["report"]["selected_document_pin"]
        require(
            document["sha256"] == registered["document_sha256"],
            "Exact independently declared document bytes required",
        )
        require(cfg["plan"]["due_at"] == slot["due_at"], "Policy due differs from native cadence")
        native_refs = [document]
        with backup.database(Path(runtime_root)) as source:
            _, _, _, receipts = policy._history(Path(runtime_root), source, cfg)
            for recipient in view["report"]["recipients"]:
                for key in ("delivery",):
                    delivered = recipient[key]
                    if delivered is None:
                        continue
                    command = delivered["command_id"]
                    receipt = receipts[command]
                    require(receipt["request"]["operation"] == "DELIVER", "Delivery receipt kind")
                # Every committed delivery/read original is retained by its exact native pin.
            for receipt in receipts.values():
                if receipt["event_at"] <= at and receipt["request"]["operation"] in {
                    "DELIVER",
                    "READ_RETURN",
                }:
                    native_refs.append(receipt["operation_pin"])
            for ref in native_refs:
                backup.native(source, ref, at)
        observation = {
            "performed_by": actor_id,
            "runtime_root": str(Path(runtime_root).absolute()),
            "runtime_sha256": runtime_sha256,
            "native_refs": native_refs,
            "recorded_policy_report": view["report"],
            "policy_state_basis": view["state_basis"],
            "status": "EXACT_LOCAL_DOCUMENT_DELIVERY_READ_RECEIPTS_BOUND",
            "human_acknowledgment": "NOT_ESTABLISHED",
            "all_recipients_delivered": all(
                r["delivery_status"] == "DELIVERED_CURRENT_VERSION"
                for r in view["report"]["recipients"]
            ),
            "all_recipients_read_return": all(
                r["read_return_current_delivery"] for r in view["report"]["recipients"]
            ),
        }
        require(
            policy._config(Path(runtime_root), runtime_sha256) == cfg,
            "Policy configuration changed during binding",
        )
        db.commit()
        return _append(store, definition, decl, slot, command_id, at, expected_version, observation)


def restore_return(
    store,
    *,
    declaration_pin,
    slot_id,
    runtime_root,
    runtime_sha256,
    criterion_pin,
    probe_pin,
    actor_id,
    command_id,
    event_at,
    expected_version=0,
):
    """Fresh parsed restore return, age, copy duration and declared local capacity.

    Existing restore/copy/use operations remain the producer. This binding performs
    another actual read and local criterion evaluation, never application/BIA approval.
    """
    at = _time(event_at)
    with writer(store), store._db() as db:
        db.execute("BEGIN")
        decl, definition, slot = _slot(db, declaration_pin, slot_id, at, "RESTORE")
        scope = (definition["company"], definition["branch"])
        require(
            exact_pin(criterion_pin)["system"] == "service_criterion",
            "Exact admitted physical service criterion role required",
        )
        criterion_row, criterion = selected(db, criterion_pin, at, scope)
        keys(
            criterion,
            "schema service_id dataset_id author_id reviewer_id approved_at "
            "max_age_seconds max_restore_seconds min_record_count qualification",
        )
        require(
            criterion["schema"] == "SH_LOCAL_SERVICE_RETURN_CRITERION_V1"
            and criterion["qualification"]
            == "LOCAL_SIMULATED_SERVICE_CRITERION_NOT_ENTERPRISE_BIA",
            "Exact local service criterion required",
        )
        require(
            criterion["author_id"] == actor_id and criterion["reviewer_id"] != actor_id,
            "Distinct named local criterion actors required",
        )
        require(
            _time(criterion["approved_at"]) == _time(criterion_row["event_at"]),
            "Criterion approval clock differs from native original",
        )
        for key in ("max_age_seconds", "max_restore_seconds", "min_record_count"):
            require(
                type(criterion[key]) is int and 1 <= criterion[key] <= 31536000,
                "Exact positive bounded service criterion",
            )
        item = next(item for item in definition["items"] if item["id"] == slot["item_id"])
        require(criterion["service_id"] == item["system_id"], "Criterion names another service")
        root = Path(runtime_root)
        cfg = backup._config(root, runtime_sha256)
        require(
            (cfg["plan"]["company_id"], cfg["plan"]["branch_id"]) == scope
            and cfg["operator_id"] == actor_id
            and cfg["operating_reviewer_id"] == criterion["reviewer_id"],
            "Exact source service runtime and actor",
        )
        # Existing census independently checks declared occurrences and configuration.
        backup.reconcile(root, expected_runtime_sha256=runtime_sha256, as_of=at)
        with backup.database(root) as source:
            probe_row = backup.native(source, probe_pin, at)
            probe = decode(probe_row["content"])
            require(
                probe_pin["system"] == "restore_use_probe"
                and probe.get("qualification") == use_probe.QUALIFICATION,
                "Exact native restore-use probe required",
            )
            contract_row = backup.native(source, probe["contract_pin"], at)
            job_row = backup.native(source, probe["restore_job_pin"], at)
            restored = backup.native(source, probe["restored_dataset_pin"], at)
            contract, job = decode(contract_row["content"]), decode(job_row["content"])
            require(
                criterion["dataset_id"] == contract["dataset_id"] == job["dataset_id"]
                and job["status"] == "COMPLETED"
                and job["object_pin"] == probe["restored_dataset_pin"]
                and contract["source_pin"] == job["comparison_source_pin"] == probe["source_pin"],
                "Exact restore dataset/source/contract joins required",
            )
            require(
                _time(criterion_row["available_at"])
                <= _time(contract_row["event_at"])
                < _time(job_row["event_at"])
                < _time(probe_row["event_at"])
                <= at,
                "Prospective criterion/use contract and restore chronology required",
            )
            relative = Path(job["copy_path"])
            require(
                not relative.is_absolute()
                and len(relative.parts) == 3
                and relative.parts[0] == "attempts"
                and relative.parts[2] == "copied.bin"
                and all(part not in {"", ".", ".."} for part in relative.parts),
                "Exact owned restored-copy path",
            )
            copied = backup.checked_bytes(root / relative)
            require(
                copied == restored["content"] and sha(copied) == probe["copy_sha256"],
                "Actual restored bytes changed",
            )
            reader = use_probe._reader(contract["reader"])
            read_status, actual = use_probe._actual(copied, reader)
            parsed = decode(copied)
            capacity = (
                len(parsed.get("records", []))
                if type(parsed) is dict and type(parsed.get("records")) is list
                else 0
            )
            age, elapsed = job["checkpoint_age_seconds"], job["actual_elapsed_seconds"]
            require(
                all(
                    type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in (age, elapsed)
                ),
                "Actual finite copy duration/data age required",
            )
            success = (
                read_status == "READ"
                and encoded(actual) == encoded(reader["expected"])
                and age <= criterion["max_age_seconds"]
                and elapsed <= criterion["max_restore_seconds"]
                and capacity >= criterion["min_record_count"]
            )
            native_refs = [
                probe_pin,
                probe["contract_pin"],
                probe["restore_job_pin"],
                probe["restored_dataset_pin"],
                probe["source_pin"],
            ]
            for ref in native_refs:
                backup.native(source, ref, at)
        observation = {
            "performed_by": actor_id,
            "recorded_review_contact": criterion["reviewer_id"],
            "criterion_pin": criterion_pin,
            "native_refs": native_refs,
            "copy_sha256": sha(copied),
            "read_status": read_status,
            "actual": actual,
            "actual_elapsed_seconds": elapsed,
            "checkpoint_age_seconds": age,
            "parsed_record_count": capacity,
            "status": "PASS_LOCAL_SERVICE_RETURN_CRITERION"
            if success
            else "FAIL_LOCAL_SERVICE_RETURN_CRITERION",
            "review_performed": False,
            "enterprise_BIA_or_application_acceptance": False,
        }
        db.commit()
        return _append(store, definition, decl, slot, command_id, at, expected_version, observation)


def restore_failure(
    store,
    *,
    declaration_pin,
    slot_id,
    runtime_root,
    runtime_sha256,
    job_pin,
    actor_id,
    command_id,
    event_at,
    expected_version=0,
):
    """Retain a genuine failed source attempt distinctly from a missing occurrence."""
    at = _time(event_at)
    with writer(store), store._db() as db:
        db.execute("BEGIN")
        decl, definition, slot = _slot(db, declaration_pin, slot_id, at, "RESTORE")
        root = Path(runtime_root)
        cfg = backup._config(root, runtime_sha256)
        require(
            (cfg["plan"]["company_id"], cfg["plan"]["branch_id"])
            == (definition["company"], definition["branch"])
            and cfg["operator_id"] == actor_id
            and job_pin["system"] == "restore_job",
            "Exact registered restore runtime/actor/job required",
        )
        census = backup.reconcile(root, expected_runtime_sha256=runtime_sha256, as_of=at)
        with backup.database(root) as source:
            job_row = backup.native(source, job_pin, at)
            job = decode(job_row["content"])
            matches = [
                h
                for occurrence in census["occurrences"]
                for h in occurrence["history"]
                if h["job_pin"] == job_pin
            ]
            require(
                len(matches) == 1
                and job["status"] == "FAILED"
                and job["operation"] == "RESTORE"
                and job["object_pin"] is None
                and job["copied_bytes"] == 0
                and job["actual_elapsed_seconds"] is None
                and type(job["error_code"]) is str
                and job["error_code"],
                "Genuine failed zero-return source restore attempt required",
            )
        observation = {
            "performed_by": actor_id,
            "job_pin": job_pin,
            "source_attempted_at": job["business_attempted_at"],
            "error_code": job["error_code"],
            "returned_bytes": 0,
            "status": "FAIL_LOCAL_RESTORE_NO_RETURN",
            "completed_copy_or_read_or_BIA_claim": False,
        }
        db.commit()
        return _append(store, definition, decl, slot, command_id, at, expected_version, observation)


def inspect(store, *, declaration_pin, as_of):
    """Fresh due census preserves all versions, unresolved scope and exclusions."""
    at = _time(as_of)
    with store._db() as db:
        db.execute("BEGIN")
        decl, definition = _declaration(db, declaration_pin, at)
        scope = (definition["company"], definition["branch"])
        observations = {}
        total = 0
        cursor = db.execute(
            "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
            "AND available_at<=? ORDER BY record,version",
            (*scope, SYSTEM, at),
        )
        for ordinal, row in enumerate(cursor):
            total += len(row["content"])
            require(
                ordinal < MAX_ROWS and total <= MAX_BYTES, "Bounded observation history exceeded"
            )
            require(sha(row["content"]) == row["sha256"], "Operating original changed")
            body = decode(row["content"].decode())
            if body["declaration_pin"] != pin(decl):
                continue
            require(
                body["schema"] == "SH_NATIVE_OPERATING_DEPTH_OBSERVATION_V1"
                and body["professional_acceptance"] == "NOT_ASSERTED",
                "Operating observation format differs",
            )
            observations.setdefault(body["slot"]["slot_id"], []).append(
                {"native": pin(row), **body}
            )
        slots = schedule(definition)
        require(set(observations) <= {s["slot_id"] for s in slots}, "Unscheduled native occurrence")
        for slot in slots:
            history = observations.get(slot["slot_id"], [])
            require(all(encoded(h["slot"]) == encoded(slot) for h in history), "Due slot changed")
            slot.update(
                history=history,
                due=slot["due_at"] <= at,
                state="EXCLUDED_OPERATING_WINDOW"
                if not slot["expected"]
                else history[-1]["observation"]["status"]
                if history
                else "MISSING_DUE"
                if slot["due_at"] <= at
                else "NOT_YET_DUE",
                late=bool(history and history[-1]["recorded_at"] > slot["due_at"]),
            )
    return {
        "declaration_pin": pin(decl),
        "as_of": at,
        "slots": slots,
        "missing_due": sum(s["state"] == "MISSING_DUE" for s in slots),
        "expected_due": sum(s["expected"] and s["due"] for s in slots),
        "enterprise_completeness_established": False,
        "qualification": QUALIFICATION,
    }
