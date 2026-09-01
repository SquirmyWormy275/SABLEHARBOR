# Known limitations

- The baseline profile is an FY2026 calibration snapshot. The `standard` profile provides a
  synthetic 2023–2026 monthly model. The seven 2016–2022 values in `full_history` are revenue
  calibration anchors only; they are not complete historical financial statements.
- Summary journals remain available as a compact calibration profile. The standard profile provides causal contract-to-cash, payroll, procurement, assets, debt, Red Wash production/sales, ARU/BS&T movements, Cradle recovery, Willow/Atlas research, and consolidation-elimination records.
- The initial proof workbook remains available for compatibility. The completed suite generates six database-controlled workbooks covering consolidation, software/services, industrial operations, close/subledgers, capital/valuation, and release control.
- Legal entities, acquisition terms, mine economics, ARU estate, Cradle structure, headcount, and consolidated values remain `MODEL_PROPOSED` or `SCENARIO_INPUT`.
- Local PostgreSQL verification on 2026-09-01 was unavailable because Docker API access to `/var/run/docker.sock` was denied, the system PostgreSQL service was inactive, and no Podman fallback was installed. CI runs migrations, standard generation, and validation against PostgreSQL 16.
- The public package is review blocked: it still uses a raw SQLite snapshot rather than building a
  new database from a versioned table-and-column allowlist, and generated CSV/SQLite/XLSX/archive
  contents do not yet pass the required comprehensive artifact safety scan.
- This is a synthetic enterprise reference platform, not audited financial statements, a reserve report, legal advice, tax advice, or a production mine/rail safety system.
