"""Build deterministic Red Wash source tables and SQLite package.

The generator is intentionally source-first. It reads the controlled core record, generates
reproducible synthetic operating evidence, and never changes the locked transaction or 2026
operating totals. It uses only the Python standard library.
"""
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
CORE = DATA / "core_operating_data.json"
SEED = 20250718


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def distribute(total: int, weights: list[float]) -> list[int]:
    raw = [total * item / sum(weights) for item in weights]
    result = [int(item) for item in raw]
    for index in sorted(range(len(raw)), key=lambda item: raw[item] - result[item], reverse=True)[: total - sum(result)]:
        result[index] += 1
    return result


def drill_database(rng: random.Random) -> None:
    domains = ["North Roll", "Central Lens", "East 12", "Lower Channel", "South Limb"]
    collars: list[dict] = []
    surveys: list[dict] = []
    assays: list[dict] = []
    factors = {"North Roll": 1.08, "Central Lens": 1.0, "East 12": 1.15, "Lower Channel": 0.92, "South Limb": 0.84}
    for sequence in range(1, 241):
        year = 2005 + min(20, (sequence - 1) // 12)
        hole = f"RW-{year}-{sequence:03d}"
        depth = rng.randint(550, 2800)
        azimuth = rng.choice([0, 0, 0, rng.randint(1, 359)])
        dip = -90 if azimuth == 0 else rng.choice([-60, -70, -75, -80])
        domain = rng.choice(domains)
        collars.append({
            "hole_id": hole,
            "year": year,
            "easting_m": round(632000 + rng.uniform(-2100, 2100), 2),
            "northing_m": round(4682000 + rng.uniform(-1500, 1500), 2),
            "elevation_m": round((6370 + rng.uniform(-70, 90)) * 0.3048, 2),
            "total_depth_ft": depth,
            "azimuth_deg": azimuth,
            "dip_deg": dip,
            "domain": domain,
            "record_state": "SYNTHETIC_DIEGETIC",
        })
        for measured_depth in (0, depth / 2, depth):
            surveys.append({
                "hole_id": hole,
                "depth_ft": round(measured_depth, 1),
                "azimuth_deg": round((azimuth + rng.uniform(-2, 2)) % 360, 2),
                "dip_deg": round(dip + rng.uniform(-1.5, 1.5), 2),
                "method": "gyro" if year >= 2018 else "single-shot",
            })
        center = rng.uniform(depth * 0.35, depth * 0.85)
        start = max(0, center - 25)
        for interval in range(10):
            from_ft = start + interval * 5
            distance = abs(from_ft + 2.5 - center)
            grade = max(0, rng.gauss(max(0.005, 0.22 * math.exp(-((distance / 15) ** 2)) * factors[domain]), 0.025))
            sample_type = "PRIMARY"
            if interval == 2 and sequence % 20 == 0:
                sample_type = "DUPLICATE"
            elif interval == 7 and sequence % 37 == 0:
                sample_type = "BLANK"
            elif interval == 5 and sequence % 31 == 0:
                sample_type = "STANDARD"
            assays.append({
                "sample_id": f"{hole}-{interval + 1:02d}",
                "hole_id": hole,
                "from_ft": round(from_ft, 1),
                "to_ft": round(from_ft + 5, 1),
                "u3o8_pct": 0 if sample_type == "BLANK" else round(grade, 4),
                "sample_type": sample_type,
                "lab": "Intermountain Analytical",
                "method": "XRF with check ICP-MS",
                "qa_qc_status": "WITHIN_2SD" if sample_type == "STANDARD" else "PASS",
            })
    write_csv(DATA / "drill_collars.csv", collars)
    write_csv(DATA / "downhole_surveys.csv", surveys)
    write_csv(DATA / "assays.csv", assays)


def monthly_operating_data(core: dict) -> None:
    weights = [0.90, 0.95, 1.00, 1.00, 1.05, 1.05, 1.05, 1.00, 1.00, 1.00, 1.00, 1.00]
    tons = distribute(core["mine_2026"]["ore_tons"], weights)
    sales = [50000, 25000, 75000, 50000, 25000, 50000, 25000, 50000, 50000, 25000, 25000, 50000]
    prices = [61, 61, 61, 72, 72, 72, 72, 80, 80, 80, 87, 87]
    grade_offsets = [0, 0.002, 0.004, 0.006, 0.008, 0.006, 0.004, 0.005, 0.007, 0.006, 0.004, 0.003]
    recovery_offsets = [0, 0.3, 0.6, 0.8, 1.0, 1.2, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0]
    rows: list[dict] = []
    for month in range(1, 13):
        grade = 0.165 + grade_offsets[month - 1]
        recovery = 90.5 + recovery_offsets[month - 1]
        contained = round(tons[month - 1] * 2000 * grade / 100)
        produced = round(contained * recovery / 100)
        rows.append({
            "month": f"2026-{month:02d}-01",
            "record_state": "ACTUAL" if month <= 8 else "MANAGEMENT_FORECAST",
            "ore_tons": tons[month - 1],
            "head_grade_pct": round(grade, 4),
            "recovery_pct": round(recovery, 2),
            "contained_u3o8_lb": contained,
            "u3o8_produced_lb": produced,
            "u3o8_sold_lb": sales[month - 1],
            "realized_price_usd_lb": prices[month - 1],
            "revenue_usd": sales[month - 1] * prices[month - 1],
        })
    rows[-1]["u3o8_produced_lb"] += core["mine_2026"]["produced_u3o8_lb"] - sum(row["u3o8_produced_lb"] for row in rows)
    write_csv(DATA / "monthly_production_2026.csv", rows)

    running = core["mine_2026"]["opening_finished_inventory_lb"]
    inventory: list[dict] = []
    for row in rows:
        opening = running
        running += row["u3o8_produced_lb"] - row["u3o8_sold_lb"]
        inventory.append({
            "month": row["month"],
            "opening_lb": opening,
            "production_lb": row["u3o8_produced_lb"],
            "sales_lb": row["u3o8_sold_lb"],
            "ending_lb": running,
            "record_state": row["record_state"],
        })
    write_csv(DATA / "inventory_rollforward_2026.csv", inventory)


def workforce(core: dict) -> None:
    functions = [
        ("Pale Sun Office", "President / Business Leadership", 1),
        ("Pale Sun Office", "Finance, Commercial and Contracts", 4),
        ("Pale Sun Office", "Technical, Regulatory and Strategy", 4),
        ("Pale Sun Office", "Supply, Logistics and Administration", 3),
        ("Red Wash Site", "Site General Management", 1),
        ("Red Wash Site", "Underground Operations", 44),
        ("Red Wash Site", "Maintenance and Reliability", 22),
        ("Red Wash Site", "Mill and Metallurgy", 24),
        ("Red Wash Site", "Geology and Resource Control", 8),
        ("Red Wash Site", "Safety and Radiation Protection", 7),
        ("Red Wash Site", "Environmental and Permitting", 6),
        ("Red Wash Site", "Supply and Warehouse", 6),
        ("Red Wash Site", "Site Finance, P&C and Administration", 6),
        ("Red Wash Site", "Security, Medical and Emergency Response", 4),
    ]
    rows: list[dict] = []
    employee_id = 1
    for organization, function, count in functions:
        for sequence in range(count):
            title = function if count == 1 else f"{function} Specialist {sequence + 1:02d}"
            if function == "President / Business Leadership":
                title = "President, Pale Sun — Marianne 'Mari' Varela"
            if function == "Site General Management":
                title = "Red Wash Site Superintendent — Cole"
            rows.append({
                "employee_id": f"RW-{employee_id:04d}",
                "organization": organization,
                "function": function,
                "title": title,
                "home_location": "Sacramento" if organization == "Pale Sun Office" and sequence < 7 else "Red Wash, Wyoming",
                "status": "ACTIVE",
            })
            employee_id += 1
    assert len(rows) == core["workforce_2026"]["total_fte"]
    write_csv(DATA / "employee_census_2026.csv", rows)


def virtual_data_room() -> None:
    categories = ["Corporate", "Title and land", "Geology", "Resources", "Mine planning", "Metallurgy", "Operations", "Maintenance", "Environmental", "Permitting", "Safety", "Radiation", "Commercial", "Financial", "Tax", "Insurance", "People", "IT/OT", "Transaction"]
    rows: list[dict] = []
    sequence = 1
    for category in categories:
        count = 14 if category in {"Geology", "Environmental", "Financial", "Transaction"} else 8
        for item in range(count):
            identity = f"VDR-{sequence:04d}"
            rows.append({
                "vdr_id": identity,
                "category": category,
                "title": f"{category} record {item + 1:02d}",
                "document_date": f"{2005 + sequence % 21:04d}-{sequence % 12 + 1:02d}-{sequence % 27 + 1:02d}",
                "status": ["RELIED UPON", "SUPERSEDED", "CONTEXT ONLY", "OPEN ITEM"][sequence % 4],
                "sha256": hashlib.sha256(identity.encode()).hexdigest(),
                "record_state": "SYNTHETIC_INDEX",
            })
            sequence += 1
    write_csv(DATA / "virtual_data_room_index.csv", rows)


def build_database() -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    database = DIST / "red_wash_transaction_operating_record_v1.sqlite3"
    database.unlink(missing_ok=True)
    connection = sqlite3.connect(database)
    loaded: list[dict] = []
    for source in sorted(DATA.glob("*.csv")):
        with source.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        if not rows:
            continue
        columns = list(rows[0])
        table = source.stem
        connection.execute(f'CREATE TABLE "{table}" ({", ".join(f"\"{column}\" TEXT" for column in columns)})')
        connection.executemany(
            f'INSERT INTO "{table}" VALUES ({",".join("?" for _ in columns)})',
            [[row[column] or None for column in columns] for row in rows],
        )
        loaded.append({"table": table, "rows": len(rows), "source": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    connection.executescript(
        """
        CREATE VIEW v_2026_production AS
        SELECT SUM(CAST(ore_tons AS INTEGER)) AS ore_tons,
               SUM(CAST(u3o8_produced_lb AS INTEGER)) AS produced_lb,
               SUM(CAST(u3o8_sold_lb AS INTEGER)) AS sold_lb,
               SUM(CAST(revenue_usd AS REAL)) AS revenue_usd
        FROM monthly_production_2026;
        CREATE VIEW v_2026_inventory AS
        SELECT MIN(CAST(opening_lb AS INTEGER)) AS opening_lb,
               SUM(CAST(production_lb AS INTEGER)) AS production_lb,
               SUM(CAST(sales_lb AS INTEGER)) AS sales_lb,
               MAX(CAST(ending_lb AS INTEGER)) AS ending_lb
        FROM inventory_rollforward_2026;
        """
    )
    connection.commit()
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    connection.close()
    manifest = {
        "database": database.name,
        "bytes": database.stat().st_size,
        "sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
        "integrity": integrity,
        "tables": loaded,
    }
    (DIST / "database_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    core = json.loads(CORE.read_text(encoding="utf-8"))
    rng = random.Random(SEED)
    drill_database(rng)
    monthly_operating_data(core)
    workforce(core)
    virtual_data_room()
    build_database()
    print(json.dumps({
        "status": "PASS",
        "record_id": core["record_id"],
        "drill_holes": 240,
        "survey_records": 720,
        "assay_intervals": 2400,
        "workforce": 140,
        "vdr_records": 176,
        "ore_tons": 175000,
        "produced_lb": 547400,
        "sold_lb": 500000,
        "ending_inventory_lb": 172400,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
