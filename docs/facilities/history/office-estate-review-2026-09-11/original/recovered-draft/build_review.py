"""Reproduce the September 11 estate review without changing canonical registers."""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from enterprise.services.model import load, footprint, json_default, saas_annual

BASE = "2b52933132e028bf5d9c9a8c151bb45cb0f19597"
CATEGORIES = {
    1: "Established location; supported fact or derivative reconciliation",
    2: "Existing site/function; working-base or people assignment unresolved",
    3: "Shared, distributed or field capability; operating-base model required",
    4: "New substantive office/facility/hosting decision",
    5: "Established region; parcel, tenure, capacity or occupancy precision unresolved",
    6: "Historical, external, provisional, superseded, asset or nonphysical record",
}

def read(path):
    return json.loads((ROOT / path).read_text())

def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=json_default) + "\n")

def csv_write(name, rows):
    with (HERE / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for row in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k,v in row.items()})

def route(ident, name="", location="", status=""):
    """Editorial review dispositions, never automatically promoted to canon."""
    if ident in ("SH-SITE-0011", "SH-SITE-0012", "SH-SITE-0013"):
        return 6, "E-05", "Provisional regional-office concept, not an operating lease; retain unless D-03 accepts an operating-base model."
    if ident == "atlas-lineage":
        return 6, "E-11", "Historical research lineage, not an additional Atlas workplace."
    if ident.startswith(("ALX", "PIN-")) or ident in ("atlas-client", "atlas-professional"):
        return 6, "E-08", "Nonphysical system/portal; hosting follows its data domain, not its own building."
    if ident.startswith("EDU-") or ident in ("J2-EDU", "FAC-EDUCATION", "SH-SITE-0014"):
        return (4 if ident in ("J2-EDU", "FAC-EDUCATION", "SH-SITE-0014") else 6), "E-03", "Education campus decision; programs share rooms and faculty."
    if ident.startswith("CONTACT-CAP") or ident in ("J2-JAG", "J2-CELL"):
        return 3, "E-02", "Field deployments and a shared J2 base; no separate collection-discipline premises."
    if ident in ("J2", "J2-HQ", "J2-CONTACT", "J2-JUDGMENT", "J2-ORIENTATION", "J2-WATCH", "SH-SITE-0015"):
        return 4, "E-02", "Separate J2 accommodation within the proposed Sacramento campus; preserve independence."
    if ident.startswith(("J2-", "GOV-", "IT-CAP-")):
        return 6, "E-02" if ident.startswith("J2-") else "E-01", "Forum, publication or capability shares its accountable owner's workplace."
    if ident.startswith("CORP-") or ident in ("SHI", "SHIH", "FAC-HQ", "SH-SITE-0001"):
        return (5 if ident in ("SHI", "CORP-CENTER", "CORP-HQ", "FAC-HQ", "SH-SITE-0001") else 2), "E-01", "Sacramento is established for HQ; separate functions need an explicit working-base assignment."
    if ident in ("foundry", "foundry-field", "SH-SITE-0017") or ident.startswith("ff-"):
        return (6 if ident == "foundry" or ident.startswith("ff-") else 3), "E-04", "Foundry is software; Foundry Field uses shared product and customer-deployment bases."
    if ident.startswith("atlas-") or ident == "SH-SITE-0018":
        return 3, "E-04", "Dedicated Atlas product organization; shared premises do not pool its staff into Advisory."
    if ident.startswith("adv") or ident == "SH-SITE-0019":
        return 3, "E-04", "One professional bench across shared Sacramento, eastern touchdown and client sites."
    if ident in ("PS", "SH-SITE-0011", "SH-SITE-0012", "SH-SITE-0013"):
        return 4, "E-07" if ident == "PS" else "E-05", "Business base/satellite decision; no office follows automatically from legal jurisdiction."
    if ident.startswith(("fort", "SH-FAC-FORT")) or ident in ("willow", "FAC-FORT", "SH-SITE-0003"):
        return 5, "E-06", "Fort concept and functions established; exact capacity, parcel and tenure remain unresolved."
    if ident in ("bedford", "project-cradle", "FAC-BEDFORD", "SH-SITE-0005"):
        return 5, "E-06", "Fairmont center established; preserve 15–20 acres and distinct external hosts."
    if ident in ("kgm", "demotte", "stream17", "demotte-gen1", "SH-SITE-0023", "SH-SITE-0027"):
        return 6, "E-10", "External host; Cradle owns intervention equipment and defined rights, not host real estate."
    if ident in ("FAC-PRIMARY", "FAC-RECOVERY", "FAC-ALEXANDRIA", "SH-SITE-0016"):
        return 4, "E-08", "Hosting facility/region is a proposal; no selected provider or installed capacity."
    if ident.startswith("ENV-"):
        return 4 if ident != "ENV-SITE" else 3, "E-09" if ident in ("ENV-SITE", "ENV-CORPORATE") else "E-08", "Apply the existing six workload classes with explicit physical and administrative boundaries."
    if ident == "FAC-OWNED":
        return 6, "E-08", "Owned data-center building remains an unselected comparison alternative."
    if ident.startswith(("SH-FAC-RW", "SH-BR-")):
        return 6, "E-11", "Artwork or synthetic historical asset; no new installed facility or geography inferred."
    if ident in ("ARU", "BST", "RWH", "red-wash-mine", "red-wash-access", "taylor-hub", "FAC-TAYLOR", "FAC-REDWASH") or ident.startswith(("FAC-TAY", "FAC-RAW", "FAC-ARU", "FAC-WAM", "FAC-EAST", "FAC-MINERAL", "FAC-RW-RECEIVING", "aru-", "BST-")):
        return 1, "E-07", "Reuse accepted industrial locations and operating populations; precision remains a separate engineering task."
    if ident in ("SH-SITE-0006", "SH-SITE-0007", "SH-SITE-0008", "SH-SITE-0020", "SH-SITE-0021"):
        return 5, "E-07", "Accepted industrial case retained; exact land/engineering precision is still bounded."
    if ident.startswith("TEAM-"):
        return 3, "E-09", "Existing functional owner or proposed skill pool; not an extra department, building or occupied hire."
    if ident.startswith(("ROLE-", "ADV-ROLE-")):
        return 2, "E-12", "Existing office/rank/engagement responsibility; no named occupant or separate premises inferred."
    return 6, "E-11", "Retain source status, historical period and ownership; no new current premises justified."

def main():
    chart = read("docs/organization/source/chartbook.json")
    geo = read("geospatial/sources/catalog.json")
    services = load()
    ops = read("industrial/source/operations.json")
    proposals = read(str(HERE.relative_to(ROOT) / "estate-proposal.json"))
    rows = []
    def add(kind, ident, name, source, loc="", status="", sources=None, extra=None):
        cat, estate, action = route(ident, name, loc, status)
        if kind == "person":
            cat, estate, action = 2 if status == "current_employee" else 6, "E-12", "Reconcile through role and existing home population; never add a person twice for multiple offices."
        if kind == "service":
            cat, estate, action = 3, "E-09", "Use linked components and accountable existing owner; service count is not site count."
        rows.append({"review_id":f"EST-{kind}-{ident}", "source_id":ident, "source_surface":kind, "name":name, "category":cat, "estate_proposal_id":estate, "current_location":loc or None, "current_status":status or None, "current_source":source, "source_references":sources or [], "disposition":action, "disposition_is_proposal":True, "detail":extra or {}})
    for n in chart["nodes"]:
        add("person" if n["type"]=="person" else "display", n["id"], n["name"], "docs/organization/source/chartbook.json", n.get("location",""), n.get("status",""), n.get("sources"), {"notes":n.get("notes",[]), "title":n.get("title"), "person_id":n.get("person_id")})
    for n in chart["register_only"]:
        add("register",n["id"],n["name"],"docs/organization/source/chartbook.json",status=n["status"],sources=n.get("sources"),extra={"reason":n.get("reason"),"detail":n.get("detail")})
    for n in geo["objects"]:
        add("geo",n["object_id"],n["canonical_name"],"geospatial/sources/catalog.json",n.get("place",""),n.get("canon_status",""),[{"path":n.get("source_path"),"locator":n.get("source_locator"),"commit":n.get("source_commit")}],{k:n.get(k) for k in ["object_type","fictionality","date_precision","notes","decision_id","relevant_date"]})
    for n in services["components"]["components"]:
        add("component",n["id"],n["name"],"enterprise/services/source/components.json",n.get("location","") or "", n.get("state",n.get("readiness","")),extra=n)
    for n in services["services"]["services"]:
        add("service",n["id"],n["name"],"enterprise/services/source/services.json",extra=n)
    for n in ops["facilities"]:
        add("industrial",n["id"],n["name"],"industrial/source/operations.json",status=n["fact_state"],extra=n)
    assert len({r["review_id"] for r in rows}) == len(rows)
    assert all(r["estate_proposal_id"] in {p["id"] for p in proposals["estate"]} for r in rows)
    assert {r["category"] for r in rows} <= set(CATEGORIES)
    write("gap-inventory.json", {"state":"PENDING_REVIEW_NOT_CANON", "base":BASE,"categories":CATEGORIES,"rows":rows})
    csv_write("gap-inventory.csv",[{k:v for k,v in r.items() if k not in ("detail","source_references")} for r in rows])
    counts=dict(collections.Counter(r["source_surface"] for r in rows))
    missing=[r for r in rows if r["source_surface"]=="display" and "not recorded" in (r["current_location"] or "").lower()]
    assert len(missing)==99
    missing_groups=collections.Counter(r["estate_proposal_id"] for r in missing)
    fp=footprint(services,"owned_colo",0)
    workforce=services["provenance"]["policy_extract"]["workforce"]
    assert sum(x["occupied"] for x in workforce.values())==506
    assert sum(x["authorized"] for x in workforce.values())==591
    assert len(geo["objects"])==175 and len(ops["facilities"])==12
    assert sum(f["assigned_fte"] for f in ops["facilities"] if f["owner"] != "Red Wash Mining, LLC")==131
    costs=[]
    for p in proposals["estate"]:
        for part in p.get("space_cost_parts",[]):
            usf=part["usable_sqft"]
            costs.append({"estate_id":p["id"], "part":part["part"], "usable_sqft":usf,"gross_sqft":round(usf/part["usable_to_gross"]),"fitout_low_usd":usf*part["fitout_usd_per_usf"][0],"fitout_high_usd":usf*part["fitout_usd_per_usf"][1],"annual_premises_low_usd":usf*part["annual_premises_usd_per_usf"][0],"annual_premises_high_usd":usf*part["annual_premises_usd_per_usf"][1],"annual_property_services_low_usd":usf*part["annual_services_usd_per_usf"][0],"annual_property_services_high_usd":usf*part["annual_services_usd_per_usf"][1]})
    campus=[x for x in costs if x["estate_id"] in ["E-01","E-02","E-03"]]
    totals={k:sum(x[k] for x in campus) for k in campus[0] if k not in ("estate_id","part")}
    write("capacity-cost-bridge.json",{"state":"SYNTHETIC_GROSS_PLANNING_NOT_FUNDING", "source_workforce":workforce,"core_occupied":506,"core_authorized":591,"industrial_hold_flat_license_scenario":271,"modeled_users":777,"j2_authorized":237,"education_included_in_j2":35,"service_footprint_base":fp,"service_license_rows":saas_annual(services),"facility_cost_parts":costs,"campus_subtotals":totals,"site_overlay":proposals["financial_bridge"],"approved_net_incremental_usd":None,"dates":"No construction, lease, opening or procurement date approved."})
    csv_write("capacity-cost-bridge.csv",costs)
    sources=set()
    for r in rows:
        sources.add(r["current_source"])
        for s in r["source_references"]:
            if s.get("path"):sources.add(s["path"])
    for p in proposals["estate"]:sources.update(p["sources"])
    sources.update(proposals["required_reading"])
    tracked=subprocess.check_output(["git","ls-tree","-r","--name-only",BASE],cwd=ROOT,text=True).splitlines()
    terms=re.compile(r"\b(?:headquarters|office|campus|facility|facilities|colocation|parcel|occupancy|Railyards|Hazelwood|Bedford|Wallaby|Glasshouse|Reno|Elko|Tucson)\b",re.I)
    scan=[]
    for path in tracked:
        p=ROOT/path
        if p.suffix.lower() not in {".md",".txt",".json",".csv",".yml",".yaml",".py",".geojson",".toml"}:
            scan.append({"path":path,"review":"BINARY_OR_OTHER_NOT_TEXT_SCREENED"});continue
        b=p.read_bytes()
        try:t=b.decode("utf-8")
        except UnicodeError:
            scan.append({"path":path,"review":"NON_UTF8_NOT_SCREENED"});continue
        matches=[i for i,line in enumerate(t.splitlines(),1) if terms.search(line)]
        scan.append({"path":path,"sha256":hashlib.sha256(b).hexdigest(),"matching_line_count":len(matches),"matching_lines":matches,"review":"REQUIRED_OR_RECORD_LINKED" if path in sources else "TEXT_DISCOVERY_ONLY"})
    source_rows=[]
    for s in sorted(sources):
        p=ROOT/s
        assert p.is_file(),s
        source_rows.append({"path":s,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"review":"STRUCTURED_PARSE_OR_DOCUMENT_SOURCE_REFERENCE; see narrative scope and limitations"})
    write("source-review.json",{"base":BASE,"baseline_same_as_handover":True,"later_main_delta":[],"source_files":source_rows,"whole_tree_discovery":scan,"limitations":["Machine parsing and lexical discovery are not full semantic adjudication of every historical source.","No new OCR, binary image census, native QGIS review or survey/title investigation.","Existing chart publication is retained byte-for-byte; no new visual authoring in this planning tranche.","Geo source snapshot remains September 7; later accepted service, finance, organization and people sources are explicitly consumed here."]})
    summary={"base":BASE,"inventory_counts":counts,"total_review_rows":len(rows),"unrecorded_display_locations":99,"unrecorded_by_estate":dict(missing_groups),"categories":dict(collections.Counter(r["category"] for r in rows)),"required_or_linked_source_files":len(source_rows),"tracked_files_screened_or_dispositioned":len(scan),"text_files_with_hits":sum(bool(r.get("matching_line_count")) for r in scan),"coverage_assertions":"PASS","source_state":"PENDING_BRANCH_REVIEW_NOT_MAIN_ACCEPTANCE"}
    write("review-summary.json",summary)
    print(json.dumps(summary,indent=2))

if __name__ == "__main__":
    main()
