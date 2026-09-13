"""A complete site requirement docket with independently bound controlling excerpts."""

import json
from collections import Counter
from geospatial.chronology.build import ROOT, archived, sha
from geospatial.closeout.sites import review

REVISION = "a8e6dd99c113e0470bdc4fcc63bab616949186d0"
CRADLE = "docs/canon/CRADLE_CLOSEOUT_2026-09-06.md"
LORE = "docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.1.md"
HANDOVER = "docs/canon/SABLE_HARBOR_CANONICAL_ARCHITECTURE_HANDOVER.md"
OBSERVATIONS = [
    (
        ["SH-SITE-0001"],
        "docs/canon/CORPORATE_HEADQUARTERS_CLOSEOUT_2026-09-03.md",
        "Headquarters is in **Sacramento, California**.",
        "LOCATION_AND_CAMPUS_DIRECTION",
        "City and institutional campus direction; no opening or lease date.",
    ),
    (
        [
            "SH-SITE-0003",
            "SH-FAC-FORT-BIG",
            "SH-FAC-FORT-SMALL",
            "SH-FAC-FORT-WHITE",
            "SH-FAC-FORT-MUSEUM",
        ],
        "docs/canon/WILLOW_KLEIN_CLOSEOUT_2026-09-06.md",
        "Willow's Pittsburgh-area physical center",
        "OPERATING_SITE_AND_COMPONENTS",
        "The operating compound and component roles are established. Component commissioning dates remain unknown.",
    ),
    (
        ["SH-SITE-0005"],
        CRADLE,
        "Bedford is located in the **Fairmont area",
        "REGIONAL_SITE_AND_SCALE",
        "15–20 acre fictional brownfield; Fairmont supersedes Belle editorial siting, not an in-world move.",
    ),
    (
        ["SH-SITE-0005", "SH-SITE-0027"],
        CRADLE,
        "Bedford is not a mine and is not the Demotte",
        "DISTINCT_SITE_IDENTITIES",
        "Do not merge Bedford and the external treatment host.",
    ),
    (
        ["SH-SITE-0023"],
        CRADLE,
        "Kelly Gang Mining is a fictional Tasmanian",
        "HOST_PROCESS_OBSERVATION",
        "The existing separation circuit and Stream 17 are established; exact host parcel and access are not.",
    ),
    (
        ["SH-SITE-0023"],
        CRADLE,
        "- Kelly Gang Mining retains operating authority",
        "HOST_AUTHORITY_AND_BYPASS",
        "Cradle equipment does not confer host-plant ownership or authority.",
    ),
    (
        ["SH-SITE-0027"],
        CRADLE,
        "Cradle's first U.S. reference deployment",
        "OPERATING_DEPLOYMENT_OBSERVATION",
        "North-central West Virginia Gen 1 deployment is operating by the closeout; source does not establish installation day or host parcel.",
    ),
    (
        ["SH-SITE-0027"],
        CRADLE,
        "Demotte operates ordinary treatment",
        "HOST_LIABILITY_BOUNDARY",
        "Mine, treatment system and remediation liabilities remain with the host.",
    ),
    (
        ["SH-SITE-0027"],
        CRADLE,
        "- the normal treatment path remains available",
        "HOST_TREATMENT_BYPASS",
        "Normal treatment remains available and the host can bypass recovery; this is operating canon, not an executed access instrument.",
    ),
    (
        ["SH-SITE-0005", "SH-SITE-0023", "SH-SITE-0027"],
        CRADLE,
        "By the closeout date it has:",
        "2026_OPERATING_SNAPSHOT",
        "Positive operating snapshot at the September 6 closeout; no backdated first occupancy or exact commissioning event.",
    ),
    (
        ["SH-SITE-0022"],
        CRADLE,
        "Wallaby remains a killed project.",
        "PROJECT_TERMINATION_STATUS",
        "A terminated project is not evidence of continuing occupancy or a newly relocated site.",
    ),
    (
        ["SH-SITE-0011", "SH-SITE-0012", "SH-SITE-0013"],
        HANDOVER,
        "A plausible broader office structure already discussed",
        "PROPOSED_OFFICE_NETWORK",
        "Reno, Elko and Tucson are proposed office roles. Neither an opened nor a closed physical office is proved by this paragraph.",
    ),
    (
        ["SH-SITE-0009"],
        LORE,
        "- Argent Ridge Mining operated Blackridge",
        "REGIONAL_HISTORICAL_MINE",
        "Nevada open-pit copper/gold and antecedent operator; detailed site coordinates and individual facility histories remain separate.",
    ),
    (
        ["SH-SITE-0010"],
        LORE,
        "The first foundational post-Blackridge incident occurs",
        "CUSTOMER_INCIDENT_LOCATION",
        "Nevada customer operation; incident geography does not establish company property or tenancy.",
    ),
    (
        ["SH-SITE-0004"],
        LORE,
        "Emberline remains active through 2025",
        "PROGRAMME_ABSORPTION",
        "End of the named programme is not a dated surrender of Charleston premises.",
    ),
    (
        ["SH-SITE-0003", "SH-SITE-0001"],
        LORE,
        "Gid remains in Pittsburgh.",
        "DISTINCT_OPERATING_CENTERS",
        "Laboratory office and Sacramento institutional connection do not establish shared parcel identity.",
    ),
    (
        ["SH-SITE-0024"],
        LORE,
        "Glasshouse attempts underground machine vision.",
        "EXPERIMENTAL_SITE_CONTEXT",
        "The incident identifies experimental activity, not a surveyed mine or occupied parcel.",
    ),
]


def excerpt(path, needle):
    raw = archived(path, REVISION)
    lines = raw.decode().splitlines()
    found = [i for i, line in enumerate(lines) if line.startswith(needle)]
    if len(found) != 1:
        raise ValueError("Ambiguous controlling excerpt: " + needle)
    i = found[0]
    end = min(len(lines), i + 10)
    return dict(
        path=path,
        revision=REVISION,
        sha256=sha(raw),
        locator=f"lines:{i + 1}-{end}",
        text="\n".join(lines[i:end]),
    )


def build():
    result, _ = review()
    observations = []
    for i, (ids, path, needle, kind, meaning) in enumerate(OBSERVATIONS, 1):
        observations.append(
            dict(
                observation_id=f"SITE-OBS-{i:03}",
                object_ids=ids,
                kind=kind,
                meaning=meaning,
                source=excerpt(path, needle),
                occupancy_start=None,
                occupancy_end=None,
            )
        )
    records = []
    for r in result["rows"]:
        oid = r["object_id"]
        if oid in ("SH-SITE-0001", "SH-SITE-0003", "SH-SITE-0005"):
            action = "Compare three dimensioned alternatives and their access tests. Select an explicit fictional site only after unresolved terrain, real-context compatibility and property-overlap screens are addressed. Occupancy history requires its own evidence."
            cls = "DIMENSIONED_ALTERNATIVES_DELIVERED_SELECTION_OPEN"
        elif oid in ("SH-SITE-0011", "SH-SITE-0012", "SH-SITE-0013"):
            action = "Confirm whether the proposed office ever opened. If so, supply or approve locality, shared/dedicated status and year-bounded entry/exit; otherwise retain as an unrealized proposal. Do not invent a closure date."
            cls = "PROPOSED_NOT_PROVED_OCCUPIED"
        elif oid in ("SH-SITE-0023", "SH-SITE-0027"):
            action = "Select fictional host geography within the accepted region and bind equipment footprint, service access and bypass to the host. Host ownership, liability and authority remain external; operating observation does not identify a parcel."
            cls = "OPERATING_HOST_GEOGRAPHY_OPEN"
        elif oid in (
            "SH-SITE-0014",
            "SH-SITE-0015",
            "SH-SITE-0017",
            "SH-SITE-0018",
            "SH-SITE-0019",
        ):
            action = "Decide dedicated versus shared/distributed premises and physical accommodation. Accepted room programmes do not establish actual residence, office tenancy or campus occupancy."
            cls = "PHYSICAL_ACCOMMODATION_DECISION_OPEN"
        elif oid in ("SH-SITE-0016", "SH-SITE-0028", "SH-SITE-0029", "SH-SITE-0030"):
            action = "Retain the accepted provider-selection/preconstruction state. Executed procurement, assigned-space, access and commissioning evidence belongs to the runtime estate workflow."
            cls = "RUNTIME_EVIDENCE_BOUNDARY"
        elif oid in ("SH-SITE-0020", "SH-SITE-0021", "SH-SITE-0026"):
            action = "Retain aggregate identity. Resolve member premises individually; do not create an extra parcel or a common occupancy interval from this collection."
            cls = "AGGREGATE_NOT_AN_ADDITIONAL_PARCEL"
        elif oid.startswith("SH-FAC-FORT-"):
            action = "Keep the Fort component linked to its parent and accepted 2024 site transition. Individual commissioning/lodging dates are unknown and must not be inherited automatically."
            cls = "COMPONENT_NOT_SEPARATE_PROPERTY"
        else:
            action = (
                r["period_meaning"]
                + " Preserve source geometry/region and obtain or approve the missing location, access or dated occupancy evidence separately."
            )
            cls = "SOURCE_BOUND_WITH_EXPLICIT_PRECISION_LIMIT"
        records.append(
            dict(
                object_id=oid,
                name=r["canonical_name"],
                disposition=cls,
                primary_source=r["source"],
                observations=[o["observation_id"] for o in observations if oid in o["object_ids"]],
                spatial_evidence=r["geometry_features"],
                occupancy_bounds=r["occupancy_bounds"],
                temporal_meaning=r["period_meaning"],
                required_action=action,
                issue_106_complete=False,
            )
        )
    return dict(
        source_revision=REVISION,
        records=records,
        observations=observations,
        counts=dict(Counter(r["disposition"] for r in records)),
        scope="All 34 stable site/component records. This docket identifies concrete next evidence or design decisions; it does not promote unresolved canon.",
    )


def write(output):
    output.mkdir(parents=True, exist_ok=True)
    data = build()
    (output / "SITE_DOCKET.json").write_text(json.dumps(data, indent=2) + "\n")
    return data


if __name__ == "__main__":
    write(ROOT / "geospatial/completion")
