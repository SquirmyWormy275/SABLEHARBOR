"""Final explicit export additions; August personnel is not September active headcount.

The subject census supplies no entitlements or authenticated identities. Blank names
outside the ten completed profiles remain stable anonymous synthetic identifiers.
Dirty previews retain the personnel provider's denial of newly available name joins.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from enterprise.ccf.company_closeout import information_policy
from enterprise.closeout import successor_records as previous
from enterprise.operations import completed_period, j2_personnel_completion
from enterprise.operations.availability import apply, repository_context

ROOT = previous.ROOT
EXTENSION = ROOT / "enterprise/closeout/source/final_export_extension.json"
visible = previous.visible
CORPORATE_UNITS = {
    "ess",
    "internal-audit",
    "corporate",
    "J2-HQ",
    "J2-CONTACT",
    "J2-EDUCATION",
    "J2-JAG",
    "J2-JUDGMENT",
    "J2-ORIENTATION",
}


def contracts():
    extension = json.loads(EXTENSION.read_text())
    previous.require(
        previous.file_hash(str(previous.EXTENSION.relative_to(ROOT)))
        == extension["predecessor_extension_sha256"],
        "Predecessor extension changed",
    )
    schema, scope = previous.contracts()
    previous.require(not set(schema) & set(extension["schema"]), "Final table collision")
    previous.require(set(extension["schema"]) == set(extension["scope"]), "Final scope incomplete")
    return schema | extension["schema"], scope | extension["scope"]


def _route(person):
    entity, unit = person["legal_employer"], person["unit"]
    if entity == "SHI":
        return entity, "CORPORATE" if unit in CORPORATE_UNITS else unit
    return entity, {
        "PS": "pale-sun",
        "RWH": "pale-sun",
        "ARU": "american-resource-utility",
        "BST": "american-resource-utility",
    }[entity]


def collect(context=None):
    context = context or repository_context(ROOT)
    extension = json.loads(EXTENSION.read_text())
    tables = previous.collect(context)
    tables.update({key: [] for key in extension["schema"]})
    profiles = j2_personnel_completion.build(context)
    people = completed_period.make_roster(completed_period.read(completed_period.SOURCE))[0]
    available = (
        max(
            datetime.fromisoformat(context["repository_source_available_at"]),
            datetime.fromisoformat("2026-09-22T00:00:00Z"),
        )
        .astimezone(UTC)
        .isoformat()
    )
    people = j2_personnel_completion.join_people(people, known_on=available, context=context)
    policy = information_policy.policy()
    subjects = information_policy.build_policy(
        people, [], expected_person_ids={p["person_id"] for p in people}
    )
    previous.require(
        len(people) == 702 and len(subjects["subject_ids"]) == 702, "Personnel population changed"
    )
    profile_pins = profiles["source_hashes"] | {
        j2_personnel_completion.SOURCE: previous.file_hash(j2_personnel_completion.SOURCE)
    }
    roster_pins = profile_pins | {
        p: previous.file_hash(p)
        for p in (
            completed_period.SOURCE,
            "docs/organization/source/chartbook.json",
            "industrial/source/finance.json",
            "red_wash/source/core_operating_data.json",
        )
    }
    policy_source = str(information_policy.SOURCE.relative_to(ROOT))
    policy_pins = {r["path"]: r["sha256"] for r in policy["sources"]} | {
        policy_source: previous.file_hash(policy_source)
    }

    def add(table, identifier, entity, unit, source, payload, pins, start, end=""):
        for path, value in pins.items():
            previous.require(previous.file_hash(path) == value, "Stale final source: " + path)
        # Payloads carry their own known-on guard too; callers cannot bypass the
        # envelope by querying an earlier source availability embedded in JSON.
        payload = apply(payload, context)
        tables[table].append(
            dict(
                record_id=identifier,
                record_type=table.upper(),
                entity=entity,
                unit=unit,
                effective_from=start,
                effective_to=end,
                effective_precision="DAY",
                available_at=available,
                recorded_at=available,
                authored_day="2026-09-22",
                fact_state="NEWLY_AUTHORED_SYNTHETIC_SUCCESSOR",
                record_origin="PUBLIC_SYNTHETIC_DIEGETIC",
                scenario="",
                source_path=source,
                source_sha256=pins[source],
                source_hashes_json=previous.canonical(pins),
                source_commit=context["repository_source_commit"],
                publication_state=context["publication_state"],
                acceptance_status="PENDING_REPOSITORY_ACCEPTANCE",
                payload_json=previous.canonical(payload),
                additional_cash_usd="0.00",
            )
        )

    for row in profiles["profiles"]:
        add(
            "final_personnel_profiles",
            row["profile_id"],
            "SHI",
            "CORPORATE",
            j2_personnel_completion.SOURCE,
            row,
            profile_pins,
            "2026-08-01",
        )
    for row in people:
        entity, unit = _route(row)
        add(
            "final_completed_people",
            row["person_id"],
            entity,
            unit,
            completed_period.SOURCE,
            row | {"population_scope": "COMPLETED_AUGUST_2026_NOT_CURRENT_ACTIVE_HEADCOUNT"},
            roster_pins,
            "2026-08-01",
            "2026-09-01",
        )
        add(
            "final_information_policy_subjects",
            "SH-POLICY-SUBJECT-" + row["person_id"],
            entity,
            unit,
            policy_source,
            dict(
                person_id=row["person_id"],
                name=row["name"],
                position_id=row["position_id"],
                population_period="2026-08",
                policy_document_id=policy["document_id"],
                implicit_grants=0,
                authenticated_principal_claim=False,
                current_active_employment_claim=False,
            ),
            roster_pins | policy_pins,
            "2026-09-22",
        )
    for row in policy["record_classes"]:
        add(
            "final_information_policy_classes",
            row["class_id"],
            "SHI",
            "CORPORATE",
            policy_source,
            dict(
                record_class=row,
                rules=policy["rules"],
                retention_years=policy["retention_years"],
                runtime_enforcement_claimed=False,
            ),
            policy_pins,
            "2026-09-22",
        )
    return tables


def validate_tables(tables, context=None):
    extension = json.loads(EXTENSION.read_text())
    old_names = set(json.loads(previous.EXTENSION.read_text())["schema"])
    previous.require(
        set(tables) == old_names | set(extension["schema"]), "Final table population mismatch"
    )
    previous.validate_tables({name: tables[name] for name in old_names}, context)
    additions = {name: tables[name] for name in extension["schema"]}
    previous._validate_structure(additions, extension)
    expected = collect(context)
    for name, rows in additions.items():
        previous.require(
            {r["record_id"]: r for r in rows} == {r["record_id"]: r for r in expected[name]},
            "Stale or incompatible final source: " + name,
        )
    return dict(
        counts={name: len(rows) for name, rows in tables.items()}, additional_cash_usd="0.00"
    )
