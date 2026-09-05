from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DIST = ROOT / "dist"
SEED = 20250718


def write_csv(name: str, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"empty dataset: {name}")
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def distribute(total: int, weights: list[float]) -> list[int]:
    raw = [total * value / sum(weights) for value in weights]
    result = [int(value) for value in raw]
    for index in sorted(range(len(raw)), key=lambda i: raw[i] - result[i], reverse=True)[: total - sum(result)]:
        result[index] += 1
    return result


def generate() -> None:
    random.seed(SEED)
    DATA.mkdir(parents=True, exist_ok=True)
    DIST.mkdir(parents=True, exist_ok=True)

    write_csv("ownership_history.csv", [
        {"owner_id":"OWN-01","owner":"Frontier Basin Minerals LLC","start_date":"2004-04-15","end_date":"2007-09-28","interest_pct":100,"transaction":"claim staking and lease assembly"},
        {"owner_id":"OWN-02","owner":"Carbon Basin Uranium Corp.","start_date":"2007-09-29","end_date":"2010-12-17","interest_pct":100,"transaction":"membership-interest acquisition"},
        {"owner_id":"OWN-03","owner":"Northstar Resources (Wyoming) LLC","start_date":"2010-12-18","end_date":"2025-07-17","interest_pct":100,"transaction":"asset and permit acquisition"},
        {"owner_id":"OWN-04","owner":"Sable Harbor / Red Wash Operating Company","start_date":"2025-07-18","end_date":"","interest_pct":100,"transaction":"equity purchase"},
    ])

    domains = ["North Roll", "Central Lens", "East 12", "Lower Channel", "South Limb"]
    factors = {"North Roll":1.08,"Central Lens":1.00,"East 12":1.15,"Lower Channel":0.92,"South Limb":0.84}
    collars: list[dict] = []
    surveys: list[dict] = []
    assays: list[dict] = []
    for index in range(1, 241):
        year = 2005 + min(20, (index - 1) // 12)
        hole = f"RW-{year}-{index:03d}"
        depth = random.randint(550, 2800)
        azimuth = random.choice([0, 0, 0, random.randint(1, 359)])
        dip = -90 if azimuth == 0 else random.choice([-60, -70, -75, -80])
        domain = random.choice(domains)
        collars.append({
            "hole_id":hole,"year_drilled":year,
            "easting_m":round(632000 + random.uniform(-2100, 2100), 2),
            "northing_m":round(4682000 + random.uniform(-1500, 1500), 2),
            "elevation_m":round((6370 + random.uniform(-70, 90)) * 0.3048, 2),
            "total_depth_ft":depth,"azimuth_deg":azimuth,"dip_deg":dip,
            "geologic_domain":domain,"record_state":"SYNTHETIC_DIEGETIC",
        })
        for measured_depth in (0, depth / 2, depth):
            surveys.append({"hole_id":hole,"depth_ft":round(measured_depth,1),"azimuth_deg":round((azimuth + random.uniform(-2,2)) % 360,2),"dip_deg":round(dip + random.uniform(-1.5,1.5),2),"method":"gyro" if year >= 2018 else "single-shot"})
        center = random.uniform(depth * 0.35, depth * 0.85)
        start = max(0, center - 25)
        for interval in range(10):
            frm = start + interval * 5
            midpoint = frm + 2.5
            base = max(0.005, 0.22 * math.exp(-(abs(midpoint - center) / 15) ** 2) * factors[domain])
            sample_type = "PRIMARY"
            if interval == 2 and index % 20 == 0:
                sample_type = "DUPLICATE"
            if interval == 7 and index % 37 == 0:
                sample_type = "BLANK"
            if interval == 5 and index % 31 == 0:
                sample_type = "STANDARD"
            grade = 0.0 if sample_type == "BLANK" else max(0, random.gauss(base, 0.025))
            assays.append({"sample_id":f"{hole}-{interval+1:02d}","hole_id":hole,"from_ft":round(frm,1),"to_ft":round(frm+5,1),"interval_ft":5.0,"u3o8_pct":round(grade,4),"sample_type":sample_type,"method":"pressed-pellet XRF with check ICP-MS","qa_qc_status":"WITHIN_2SD" if sample_type == "STANDARD" else "PASS"})
    write_csv("drill_collars.csv", collars)
    write_csv("downhole_surveys.csv", surveys)
    write_csv("assays.csv", assays)

    write_csv("resource_estimate_history.csv", [
        {"estimate_id":"RE-2008-01","effective_date":"2008-09-30","classification":"historical indicated","tons":1100000,"grade_u3o8_pct":0.180,"contained_lb":3960000,"recoverable_lb":3405600,"model_version":"CB-RW-2008"},
        {"estimate_id":"RE-2011-02","effective_date":"2011-12-31","classification":"internal measured+indicated","tons":1850000,"grade_u3o8_pct":0.172,"contained_lb":6364000,"recoverable_lb":5663960,"model_version":"NS-RW-2011"},
        {"estimate_id":"RE-2016-03","effective_date":"2016-12-31","classification":"internal indicated","tons":2300000,"grade_u3o8_pct":0.165,"contained_lb":7590000,"recoverable_lb":6755100,"model_version":"NS-RW-2016"},
        {"estimate_id":"RE-2024-04","effective_date":"2024-12-31","classification":"internal indicated including reserve basis","tons":2500000,"grade_u3o8_pct":0.170,"contained_lb":8500000,"recoverable_lb":7820000,"model_version":"NS-RW-2024"},
        {"estimate_id":"RE-2025-DD","effective_date":"2025-06-20","classification":"Sable Harbor acquisition basis","tons":2500000,"grade_u3o8_pct":0.170,"contained_lb":8500000,"recoverable_lb":7820000,"model_version":"SH-RW-DD-2025"},
        {"estimate_id":"RE-2025-INF","effective_date":"2025-06-20","classification":"inferred exploration inventory","tons":900000,"grade_u3o8_pct":0.145,"contained_lb":2610000,"recoverable_lb":2270700,"model_version":"SH-RW-DD-2025"},
    ])

    weights = [.90,.95,1,1,1.05,1.05,1.05,1,1,1,1,1]
    tons = distribute(175000, weights)
    sales = [50000,25000,75000,50000,25000,50000,25000,50000,50000,25000,25000,50000]
    prices = [61,61,61,72,72,72,72,80,80,80,87,87]
    production: list[dict] = []
    for month in range(1, 13):
        grade = 0.165 + [0,.002,.004,.006,.008,.006,.004,.005,.007,.006,.004,.003][month-1]
        recovery = 90.5 + [0,.3,.6,.8,1,1.2,1.5,1.6,1.7,1.8,1.9,2][month-1]
        produced = round(tons[month-1] * 2000 * grade / 100 * recovery / 100)
        production.append({"month":f"2026-{month:02d}-01","record_state":"ACTUAL" if month <= 8 else "MANAGEMENT_FORECAST","ore_tons":tons[month-1],"head_grade_u3o8_pct":round(grade,4),"recovery_pct":round(recovery,2),"contained_u3o8_lb":round(tons[month-1]*2000*grade/100),"u3o8_produced_lb":produced,"u3o8_sold_lb":sales[month-1],"realized_price_usd_per_lb":prices[month-1],"revenue_usd":sales[month-1]*prices[month-1]})
    production[-1]["u3o8_produced_lb"] += 547400 - sum(row["u3o8_produced_lb"] for row in production)
    write_csv("monthly_production_2026.csv", production)

    contracts = [
        {"contract_id":"UCA-2019-04","buyer":"Prairie States Electric Cooperative","committed_lb":150000,"pricing_type":"base-escalated term","modeled_realized_usd_lb":61,"delivery_point":"licensed conversion facility, Illinois","title_transfer":"after receipt and final assay"},
        {"contract_id":"UCA-2024-11","buyer":"Great Basin Nuclear Supply Pool","committed_lb":150000,"pricing_type":"market-related term with collar","modeled_realized_usd_lb":72,"delivery_point":"licensed conversion facility, Illinois","title_transfer":"after receipt and final assay"},
        {"contract_id":"UCA-2025-03","buyer":"Heartland Atomic Power LLC","committed_lb":125000,"pricing_type":"fixed-price term","modeled_realized_usd_lb":80,"delivery_point":"licensed conversion facility, Illinois","title_transfer":"after receipt and final assay"},
        {"contract_id":"SPOT-2026-01","buyer":"Continental Nuclear Trading LLC","committed_lb":75000,"pricing_type":"discretionary placement","modeled_realized_usd_lb":87,"delivery_point":"licensed conversion facility, Illinois","title_transfer":"after receipt and final assay"},
    ]
    write_csv("uranium_contracts.csv", contracts)

    inventory: list[dict] = []
    opening = 125000
    for row in production:
        ending = opening + row["u3o8_produced_lb"] - row["u3o8_sold_lb"]
        inventory.append({"month":row["month"],"opening_finished_u3o8_lb":opening,"production_u3o8_lb":row["u3o8_produced_lb"],"sales_u3o8_lb":row["u3o8_sold_lb"],"ending_finished_u3o8_lb":ending})
        opening = ending
    write_csv("inventory_rollforward_2026.csv", inventory)

    roles = [("Mine Operations",44),("Maintenance",22),("Mill and Process",24),("Geology and Resource",8),("Safety and Radiation",7),("Environmental and Permitting",6),("Supply and Warehouse",6),("Site Administration",6),("Emergency and Security",4),("Site General Manager",1),("Pale Sun Business Layer",12)]
    employees: list[dict] = []
    identifier = 1
    for function, count in roles:
        for _ in range(count):
            employees.append({"employee_id":f"RW-{identifier:04d}","employer":"Sable Harbor" if function == "Pale Sun Business Layer" else "Red Wash Operating Company","function":function,"site":"Red Wash / Sacramento" if function == "Pale Sun Business Layer" else "Red Wash","status":"ACTIVE","record_state":"SYNTHETIC_DIEGETIC"})
            identifier += 1
    write_csv("employee_census_2026.csv", employees)

    write_csv("permit_register.csv", [
        {"permit_id":"RW-PER-001","permit":"BLM Plan of Operations","number":"DOI-BLM-WY-C050-RW-2011-01","authority":"Bureau of Land Management","effective_date":"2011-11-18","status":"active","legal_basis":"43 CFR Subpart 3809"},
        {"permit_id":"RW-PER-002","permit":"Environmental Assessment and FONSI","number":"DOI-BLM-WY-C050-2011-0042-EA","authority":"Bureau of Land Management","effective_date":"2011-10-07","status":"active record","legal_basis":"NEPA"},
        {"permit_id":"RW-PER-003","permit":"Non-coal mine permit","number":"RW-PT-0617","authority":"Wyoming DEQ Land Quality Division","effective_date":"2012-02-14","status":"active","legal_basis":"Wyoming Environmental Quality Act"},
        {"permit_id":"RW-PER-004","permit":"Source-material license","number":"WYSML-094","authority":"Wyoming DEQ Uranium Recovery Program","effective_date":"2018-09-30","status":"active","legal_basis":"10 CFR Part 40 Appendix A / Agreement State"},
        {"permit_id":"RW-PER-005","permit":"Air-quality permit","number":"AQD-RW-1452","authority":"Wyoming DEQ Air Quality Division","effective_date":"2012-03-22","status":"active","legal_basis":"Wyoming air-quality standards"},
        {"permit_id":"RW-PER-006","permit":"Groundwater protection permit","number":"GW-RW-2012-19","authority":"Wyoming DEQ Water Quality Division","effective_date":"2012-04-30","status":"active with corrective-action schedule","legal_basis":"Wyoming groundwater protection"},
        {"permit_id":"RW-PER-007","permit":"MSHA mine identification","number":"48-01999","authority":"Mine Safety and Health Administration","effective_date":"2012-05-18","status":"active","legal_basis":"30 CFR metal/nonmetal"},
        {"permit_id":"RW-PER-008","permit":"Hazardous-material registration","number":"PHMSA-RW-2026","authority":"PHMSA","effective_date":"2026-07-01","status":"active","legal_basis":"49 CFR"},
    ])

    findings = [
        ("DD-001","Geology","HIGH","East 12 continuity exceeded direct drilling support.","Exclude unsupported stopes from base case."),
        ("DD-002","Grade Control","MEDIUM","Historical cutoff definitions changed without one effective-date register.","Reconstruct and preserve periods."),
        ("DD-003","Metallurgy","HIGH","Carbonate-rich feed produced nonlinear acid consumption and recovery.","Constrain blend and update model."),
        ("DD-004","Environment","HIGH","Cell 1 underdrain and MW-17 were not interpreted together.","Increase closure basis, corrective action and escrow."),
        ("DD-005","ARO","HIGH","Seller closure estimate omitted monitoring and demolition scopes.","Use $25M current cost and $16M opening ARO."),
        ("DD-006","Maintenance","HIGH","Executable backlog exceeded seller schedule by approximately $5.6M.","Fund H2 stabilization."),
        ("DD-007","Ventilation","HIGH","Main exhaust controls lacked reliable redundancy.","Install redundancy and stop criteria."),
        ("DD-009","Inventory","HIGH","Drum ledger contained moisture/assay timing inconsistencies.","Reweigh, assay and reseal."),
        ("DD-010","Contracts","MEDIUM","One escalation workbook used the wrong reference month.","Recalculate and obtain acknowledgment."),
        ("DD-013","Title","HIGH","Two easements remained in predecessor names.","Cure and insure through escrow."),
        ("DD-015","Safety","HIGH","Combined-condition stop authority was undocumented.","Formalize disposition authority."),
        ("DD-018","People","HIGH","Cole and five veterans held undocumented operating continuity.","Retention and succession plan."),
        ("DD-019","QoE","HIGH","Reported EBITDA included inventory liquidation and capitalized repairs.","Normalize $7.1M to $2.4M."),
        ("DD-021","Cyber/OT","MEDIUM","Mill historian and business network shared unmanaged trust.","Segment before remote product work."),
        ("DD-024","Logistics","MEDIUM","Custody source clocks did not reconcile.","Preserve source times and hold movement."),
        ("DD-025","Community","MEDIUM","Restart plan underweighted consultation schedule.","Carry schedule contingency."),
    ]
    write_csv("diligence_findings.csv", [{"finding_id":a,"domain":b,"severity":c,"finding":d,"disposition":e,"status":"EXECUTIVE_TRACKING"} for a,b,c,d,e in findings])

    write_csv("transaction_timeline.csv", [{"date":a,"event":b} for a,b in [
        ("2024-08-19","Mari Varela opens western uranium graveyard review."),("2024-10-18","Mutual NDA executed."),("2024-11-01","Virtual data room opens."),("2025-01-17","Indicative offer submitted at $34.0M subject to liabilities."),("2025-02-07","LOI signed at $38.0M headline operating value."),("2025-03-14","East 12 continuity issue identified."),("2025-03-27","MW-17 and underdrain records connected."),("2025-04-11","Seller raises expectation to $48.0M."),("2025-05-05","Sable Harbor terminates exclusivity and drafting."),("2025-05-29","Northstar returns with liability-retention proposal."),("2025-06-06","Revised term sheet sets $42.0M operating value and $28.0M cash."),("2025-06-20","Final technical and QoE reports issued."),("2025-06-27","Sable Harbor Board authorizes transaction."),("2025-07-02","Equity Purchase Agreement signed."),("2025-07-18","Transaction closes."),("2025-09-14","Cole exercises temporary stop authority."),("2026-08-31","Current evidence cutoff."),
    ]])

    write_csv("purchase_price_allocation.csv", [
        {"line":"Acquired current assets","amount_usd":4500000,"classification":"asset"},
        {"line":"Mineral properties and mine development","amount_usd":24000000,"classification":"asset"},
        {"line":"Mill and processing plant","amount_usd":14000000,"classification":"asset"},
        {"line":"Surface infrastructure and mobile equipment","amount_usd":4000000,"classification":"asset"},
        {"line":"Asset retirement obligation","amount_usd":-16000000,"classification":"liability"},
        {"line":"Other assumed liabilities","amount_usd":-2500000,"classification":"liability"},
        {"line":"Net identifiable assets","amount_usd":28000000,"classification":"subtotal"},
        {"line":"Cash consideration","amount_usd":-28000000,"classification":"consideration"},
        {"line":"Goodwill / bargain purchase","amount_usd":0,"classification":"result"},
    ])
    write_csv("quality_of_earnings.csv", [
        {"line":"Seller-reported 2024 EBITDA","amount_usd":7100000},
        {"line":"Inventory liquidation benefit","amount_usd":-2700000},
        {"line":"Capitalized repair normalization","amount_usd":-1100000},
        {"line":"Deferred environmental monitoring","amount_usd":-500000},
        {"line":"Related-party service undercharge","amount_usd":-400000},
        {"line":"Normalized 2024 EBITDA","amount_usd":2400000},
    ])
    write_csv("financial_statements_2026.csv", [
        {"statement":"Income Statement","line":"Uranium revenue","amount_usd":36475000},
        {"statement":"Income Statement","line":"Cash production cost of sales","amount_usd":-24954068},
        {"statement":"Income Statement","line":"DD&A in cost of sales","amount_usd":-3124839},
        {"statement":"Income Statement","line":"Production and mineral taxes","amount_usd":-2125000},
        {"statement":"Income Statement","line":"Royalties","amount_usd":-729500},
        {"statement":"Income Statement","line":"Freight, assay and handling","amount_usd":-600000},
        {"statement":"Income Statement","line":"Gross profit","amount_usd":4941594},
        {"statement":"Income Statement","line":"Pale Sun business and site G&A","amount_usd":-2800000},
        {"statement":"Income Statement","line":"Operating income","amount_usd":2141594},
        {"statement":"Income Statement","line":"ARO accretion","amount_usd":-1040000},
        {"statement":"Income Statement","line":"Income tax","amount_usd":-198287},
        {"statement":"Income Statement","line":"Net income","amount_usd":903307},
        {"statement":"Cash Flow","line":"Operating cash flow","amount_usd":1522213},
        {"statement":"Cash Flow","line":"Sustaining and rehabilitation capital","amount_usd":-9000000},
        {"statement":"Cash Flow","line":"Free cash flow","amount_usd":-7477787},
    ])

    monitoring: list[dict] = []
    for year in range(2019, 2027):
        for quarter in range(1, 5):
            for station in ("MW-12","MW-17","MW-21","TAIL-UD-1"):
                trend = (year-2019)*0.7 + quarter*0.12 if station == "MW-17" else random.uniform(-0.3,0.3)
                monitoring.append({"period":f"{year}-Q{quarter}","station":station,"uranium_mg_l":round(max(0.002,0.012+trend*0.002+random.uniform(-0.002,0.002)),4),"sulfate_mg_l":round(180+trend*18+random.uniform(-12,12),1),"pH":round(7.2+random.uniform(-0.25,0.25),2),"record_state":"SYNTHETIC_DIEGETIC"})
    write_csv("environmental_monitoring.csv", monitoring)

    backlog: list[dict] = []
    major = [("UG-VENT","Main ventilation fan and VFD",1450000,"critical",580000),("UG-GC","Ground-support rehabilitation",1250000,"critical",500000),("MILL-MCC","Mill motor-control centers",1100000,"high",660000),("TAIL-UD","Tailings underdrain pumps/instrumentation",900000,"critical",360000),("MILL-LEACH","Leach tanks and agitators",720000,"high",432000),("UG-DEW","Dewatering pumps and controls",680000,"high",408000),("FLEET-LHD","LHD overhaul program",640000,"high",384000),("POWER-SUB","Substation relay modernization",825000,"critical",330000)]
    for index,(system,description,cost,priority,seller) in enumerate(major,1):
        backlog.append({"backlog_id":f"MB-{index:03d}","system_id":system,"description":description,"estimated_cost_usd":cost,"priority":priority,"seller_schedule_usd":seller,"status":"funded in stabilization plan"})
    for index in range(len(major)+1,61):
        cost = random.randint(35000,120000)
        backlog.append({"backlog_id":f"MB-{index:03d}","system_id":random.choice(["ENV-WELL","SURF-BLDG","OT-NET","MILL-PUMP","UG-ELEC"]),"description":f"Deferred corrective work package {index}","estimated_cost_usd":cost,"priority":random.choice(["low","medium","high"]),"seller_schedule_usd":round(cost*random.uniform(.35,.8)),"status":random.choice(["scheduled","monitored","funded"])})
    write_csv("maintenance_backlog.csv", backlog)

    categories = ["Corporate","Title","Geology","Resource","Mine Plan","Metallurgy","Permits","Environment","Safety","Commercial","Finance","Tax","People","Insurance","Technology","Transaction"]
    write_csv("virtual_data_room_index.csv", [{"vdr_id":f"VDR-{index:04d}","category":categories[(index-1)%len(categories)],"document":f"{categories[(index-1)%len(categories)]} record {index:03d}","effective_date":f"{2005+(index%21):04d}-{1+(index%12):02d}-{1+(index%27):02d}","state":"SYNTHETIC_DIEGETIC","review_status":"reviewed" if index%7 else "exception noted"} for index in range(1,177)])

    build_database()


def build_database() -> None:
    db_path = DIST / "red_wash_transaction_operating_record_v1.sqlite3"
    db_path.unlink(missing_ok=True)
    db = sqlite3.connect(db_path)
    loaded: list[dict] = []
    for path in sorted(DATA.glob("*.csv")):
        with path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        if not rows:
            continue
        columns = list(rows[0])
        name = path.stem.replace("-", "_")
        db.execute(f'DROP TABLE IF EXISTS "{name}"')
        db.execute(f'CREATE TABLE "{name}" ({", ".join(f"[{column}] TEXT" for column in columns)})')
        db.executemany(f'INSERT INTO "{name}" VALUES ({",".join("?" for _ in columns)})', [[row[column] for column in columns] for row in rows])
        loaded.append({"table":name,"rows":len(rows),"source":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    db.executescript("""
    CREATE VIEW v_2026_production_reconciliation AS
      SELECT SUM(CAST(ore_tons AS REAL)) ore_tons,
             SUM(CAST(contained_u3o8_lb AS REAL)) contained_lb,
             SUM(CAST(u3o8_produced_lb AS REAL)) produced_lb,
             SUM(CAST(u3o8_sold_lb AS REAL)) sold_lb,
             SUM(CAST(revenue_usd AS REAL)) revenue_usd
      FROM monthly_production_2026;
    CREATE VIEW v_diligence_severity AS
      SELECT severity, COUNT(*) finding_count FROM diligence_findings GROUP BY severity;
    """)
    db.execute("CREATE TABLE package_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    db.executemany("INSERT INTO package_metadata VALUES(?,?)", {"record_id":"SH-PS-RW-TOR-001","version":"1.0.0","as_of_date":"2026-08-31","classification":"PUBLIC_SYNTHETIC_DIEGETIC"}.items())
    db.commit()
    integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    db.close()
    manifest = {"database":db_path.name,"bytes":db_path.stat().st_size,"sha256":hashlib.sha256(db_path.read_bytes()).hexdigest(),"integrity_check":integrity,"tables":loaded}
    (DIST / "red_wash_database_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    generate()
    print(json.dumps({"status":"PASS","record_id":"SH-PS-RW-TOR-001","seed":SEED,"data_files":len(list(DATA.glob('*.csv')))}, indent=2))
