# FF-003 billing quality review

**Reviewed:** September 13, 2026 · **Package:** SH-FIN-BILL-001 v1.0.0

Two independent read-only reviews checked the source arithmetic and primary-source tax
treatment before integration. The legal issuer matches the accepted entity perimeter.
All fourteen fields have dispositions; all three original billing decisions are resolved.

## Visual inspection

Rendered the one-page invoice PDF and all four workbook sheets through LibreOffice to four
US Letter landscape pages. Inspected every page as a 1.5× raster at readable resolution.
The approved Foundry Field logo is present and undistorted. Customer/issuer identities,
invoice references, amounts, notes and footer fit; no clipped columns or extra blank pages.
Corrected the rate cell's vertical alignment and bottom rule to match adjoining value cells.
The established Foundry Field letterhead and accepted workbook styles are reused.

## Numerical and preservation controls

The validator recomputes the principal and tax using Decimal, balances each of the six
source journals and the supplemental tax journal, checks exact source-row equality, verifies
all field dispositions, and binds generated assets and inputs by SHA-256. Negative tests
reject double-counted recovery, a reversed but balanced journal, a tax-inclusive divisor,
missing decisions, cross-customer joins, and promotion of forecast records to actuals.

The workbook's formulas are also recalculated by LibreOffice during print review: customer
total $1,740,000; tax expense/payable $152,250; surviving written-off claim $971,500; principal
and tax-journal check cells zero. The original source's twelve journal lines balance at
$3,813,500 on each side. The supplement contains two lines totaling $152,250 on each side.

Reproduction commands:

```bash
python tools/documents/billing_record.py build
python tools/documents/billing_record.py validate
python -m pytest -q tests/publications/test_billing_record.py --confcutdir=tests/publications
python tools/documents/approval_guard.py
python tools/documents/build_controlled_publications.py --normalizer pypdf
python tools/documents/build_institutional_catalog.py
python scripts/validate_reader_navigation.py --check-regeneration
```

Repeated generation is compared through the complete artifact manifest. Exact outputs are
bound by [manifest.json](manifest.json). The PR records the repository-wide local results
and GitHub checks at the submitted commit. Native financial releases, original proposal
bytes and approved earlier artwork remain preserved. This review makes no tax-payment,
real-world execution or future-rate-certification claim.
