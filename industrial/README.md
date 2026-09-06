# Sable Harbor industrial case

Pale Sun, Red Wash, American Resource Utility (ARU), and Blood, Sweat & Tears Railway (BS&T) form one selected industrial case. Start with the [participant guide](CASE_GUIDE.md), [legal structure](corporate/LEGAL_STRUCTURE_AND_FORMATION.md), and [implementation decisions](IMPLEMENTATION_DECISIONS.md).

The case cutoff is **September 5, 2026, 23:59:59 America/Los_Angeles**. Historical-looking company records are synthetic reconstructions. Model approval, evidence provenance, and temporal availability are separate fields. September–December 2026 monthly results are forecasts; an earlier month in a synthetic calibration is still not an audited actual.

## Build and verify

From the repository root, with Python 3.12 or later:

```bash
python industrial/tools/build_package.py --allow-working-tree
python -m unittest discover -s industrial/tests -v
```

The development flag permits an explicitly marked working-tree preview. Omit it to build a release from a clean source commit. The builder regenerates the mine, operating registers, financial schedules, selected CSV/SQLite corpus, lineage manifest, member checksums, and deterministic ZIP. Outputs go to ignored `industrial/generated/` and `industrial/dist/`. The checked-in [participant catalog](source/participant_catalog.json) is an explicit reviewed allowlist; it is not a repository dump.

The [release index](../docs/releases/INDUSTRIAL_CASE_RELEASES.md) records the distributed archive and its exact source commit. Release archives are GitHub Release assets; approved images, current SVG maps, controlled publications, source models, and executable builders remain in Git.

## Model perimeter

The [finance bridge](../docs/finance/INDUSTRIAL_FINANCE_BRIDGE_v1.0.md) connects the selected industrial books and leaves the reproducible enterprise finance-platform v0.1 snapshot intact. This case includes the industrial acquisition/funding layer and operating elimination schedules. It does not invent a revised enterprise-wide revenue, headcount, or valuation for unrelated businesses.

The original mine standalone calculation remains a named comparison. Its integrated successor includes the interface, rolled-forward ARO, incremental service costs and equity funding. The source models distinguish recurring operating costs, sustaining capital, catch-up capital, interface capital, acquisition consideration, retained debt and reserves. A balanced ledger is necessary; it does not establish engineering certification, economic attractiveness or regulatory approval.
