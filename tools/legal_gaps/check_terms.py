#!/usr/bin/env python3
"""Check draft legal schedule facts against accepted sources; never adopt draft terms."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path("docs/legal/gap-instruments")


def load(root: Path, path: str | Path):
    return json.loads((root / path).read_text())


def number(value) -> Decimal:
    return Decimal(str(value).replace(",", "").replace("$", ""))


def rows(document):
    for schedule in document["financial_schedules"]:
        columns = schedule["columns"]
        for row in schedule["rows"]:
            if len(columns) != len(row):
                raise ValueError(f"{document['gap_id']}: financial row width differs")
            yield dict(zip(columns, row, strict=True))


def markdown_rows(text: str):
    for line in text.splitlines():
        if line.startswith("|"):
            yield [
                cell.strip().replace("**", "").replace("`", "")
                for cell in line.strip("|").split("|")
            ]


def check(root: Path = ROOT) -> tuple[list[str], list[str]]:
    errors, checks = [], []

    def equal(actual, expected, label):
        if actual != expected:
            errors.append(f"{label}: {actual!r} != source {expected!r}")
        else:
            checks.append(label)

    try:
        gaps = load(root, "docs/reader/transactions/gaps.json")
        drafts = {}
        texts = {}
        for gap in gaps:
            slug = gap["id"].removeprefix("LEGAL-GAP-").lower()
            path = PACKAGE / "source" / f"{slug}.json"
            drafts[slug] = load(root, path)
            texts[slug] = (root / path.with_suffix(".md")).read_text()
            equal(drafts[slug]["status"], "DRAFT_FOR_REVIEW", f"{slug} remains draft")
            equal(drafts[slug]["gap_id"], gap["id"], f"{slug} gap identity")
            list(rows(drafts[slug]))
        finance = load(root, "industrial/source/finance.json")
        txn = finance["transaction"]
        entities = load(root, "industrial/source/entities.json")
        employer = {row["name"]: row["entity_id"] for row in entities["named_aru_leaders"]}
        retention = [r for r in rows(drafts["workforce"]) if "employee" in r]
        equal(
            len(retention),
            len(txn["retention_allocations"]),
            "individual retention schedule coverage",
        )
        equal(
            {r["employee"]: r["total_usd"] for r in retention},
            txn["retention_allocations"],
            "retention recipient/amount equality",
        )
        equal(sum(r["total_usd"] for r in retention), txn["retention_pool"], "retention pool total")
        for r in retention:
            equal(
                r["july_7_2026_usd"] + r["january_7_2027_usd"],
                r["total_usd"],
                f"{r['employee']} installments",
            )
            equal(r["july_7_2026_usd"], r["total_usd"] / 2, f"{r['employee']} first installment")
            equal(r["employer_entity_id"], employer[r["employee"]], f"{r['employee']} employer")
        for column in ["july_7_2026_usd", "january_7_2027_usd"]:
            equal(sum(r[column] for r in retention), txn["retention_pool"] / 2, f"{column} total")
        for r in retention:
            match = re.search(
                rf"### Schedule {re.escape(r['schedule'])} — {re.escape(r['employee'])}"
                r"\n\n(.*?)(?=\n###|\n##|\Z)",
                texts["workforce"],
                re.DOTALL,
            )
            if match is None:
                errors.append(f"Missing individual Markdown retention schedule: {r['schedule']}")
            else:
                amounts = [
                    number(value)
                    for value in re.findall(r"\*\*\$([0-9,]+)(?: USD)?\*\*", match.group(1))
                ]
                equal(
                    amounts,
                    [
                        number(r["total_usd"]),
                        number(r["july_7_2026_usd"]),
                        number(r["january_7_2027_usd"]),
                    ],
                    f"{r['employee']} Markdown award amounts",
                )
        carry_source = (root / "docs/advisory/CARRY_PLAN_STANDARD.md").read_text()
        carry_patterns = {
            "excess_profit_pool": r"Pool equals \*\*(\d+)%",
            "notional_pool": r"represented by \*\*([0-9,]+) notional",
            "default_vesting_years": r"Default vesting is \*\*(five) years",
            "annual_vesting": r"years, (\d+)% per completed year",
        }
        carry_expected = {}
        for key, pattern in carry_patterns.items():
            match = re.search(pattern, carry_source)
            if not match:
                raise ValueError(f"Unrecognized carry source rule {key}")
            carry_expected[key] = 5 if match.group(1) == "five" else number(match.group(1))
        equal(
            {r["measure"]: number(r["value"]) for r in rows(drafts["carry"])},
            carry_expected,
            "carry constants exactly preserve source plan",
        )
        consultant = next(r for r in rows(drafts["workforce"]) if "consultant" in r)
        equal(consultant["total_usd"], txn["seller_consulting_total"], "consulting fee")
        equal(consultant["source_start"], txn["close"], "consulting start")
        equal(consultant["source_end"], txn["seller_consulting_end"], "consulting end")
        equal(consultant["paid_status"], "NOT_ESTABLISHED", "consulting not payment evidence")

        # Check actual Markdown financial table cells against source-derived values.
        # Labels locate specific assertions, not generic vocabulary or a word-count proxy.
        def table_value(slug, label, expected, column=1):
            matching = [r for r in markdown_rows(texts[slug]) if r and r[0] == label]
            equal(len(matching), 1, f"{slug} unique financial row {label}")
            if len(matching) == 1:
                equal(number(matching[0][column]), number(expected), f"{slug}: {label}")

        uses = txn["buyer_consideration"] + txn["existing_term_revolver_refinance"]
        sources = txn["new_debt"] + txn["parent_equity_before_fees"]
        equal(uses, sources, "ARU accepted sources equal uses")
        for label, amount in {
            "Buyer-funded share consideration": txn["buyer_consideration"],
            "Old term/revolver payoff": txn["existing_term_revolver_refinance"],
            "Total uses before fees": uses,
            "New term advance": txn["new_debt"],
            "Parent equity before fees": txn["parent_equity_before_fees"],
            "Total sources before fees": sources,
            "Transaction/legal/adviser expense funding": txn["transaction_expense"],
            "Debt issuance cost funding": txn["debt_issuance_cost"],
            "Parent cash including fees": txn["parent_equity_before_fees"]
            + txn["transaction_expense"]
            + txn["debt_issuance_cost"],
        }.items():
            table_value("debt-liens", label, amount)
        bridge = load(root, "docs/finance/evidence/tax-transaction/CURRENT_SOURCE_BRIDGE.json")[
            "ppa"
        ]
        tax = bridge["tax_allocation"]
        for label, amount in {
            "Buyer stock consideration": txn["buyer_consideration"],
            "Recognized assumed liabilities in tax model": tax[
                "recognized_assumed_liabilities_usd"
            ],
            "Modeled adjusted grossed-up basis": tax["modeled_agub_usd"],
            "Other tax asset bases": sum(tax["other_tax_asset_bases_usd"].values()),
            "Residual tax goodwill": tax["tax_goodwill_basis_usd"],
            "Environmental and claim reserves": txn["environment_reserve"] + txn["claim_reserve"],
            "Conditional reserve DTA": bridge["deferred_tax_asset_usd"],
            "Identifiable book net assets": bridge[
                "identifiable_net_assets_before_refinancing_usd"
            ],
            "Book goodwill": bridge["goodwill_usd"],
            "Initial book goodwill excess over tax basis": bridge[
                "initial_book_goodwill_excess_over_tax_usd"
            ],
        }.items():
            table_value("tax-filing", label, amount)
        equal(
            tax["modeled_agub_usd"] - sum(tax["other_tax_asset_bases_usd"].values()),
            tax["tax_goodwill_basis_usd"],
            "independent tax goodwill residual",
        )
        equal(
            txn["buyer_consideration"] - bridge["identifiable_net_assets_before_refinancing_usd"],
            bridge["goodwill_usd"],
            "book goodwill residual",
        )

        def source_millions(path, phrase):
            source = (root / path).read_text()
            match = re.search(phrase, source)
            if not match:
                raise ValueError(f"Cannot locate source financing amount: {path}")
            return number(match.group(1)) * 1000000

        hv = source_millions(
            "docs/governance/board-records/2021-06-18_harrison-vale-growth-financing-minutes.md",
            r"approximately \*\*\$(\d+) million\*\* growth financing",
        )
        wr = source_millions(
            "docs/governance/board-records/2022-10-28_wolf-ridge-industrial-financing-minutes.md",
            r"approximately \*\*\$(\d+) million\*\* financing",
        )
        post = source_millions(
            "docs/governance/board-records/2022-10-28_wolf-ridge-industrial-financing-minutes.md",
            r"approximately \*\*\$(\d+) million post-money",
        )
        table_value("financing-documents", "Approximate gross financing", hv)
        table_value("financing-documents", "Approximate gross financing", wr, 2)
        table_value("financing-documents", "Approximate post-money model", post, 2)

        runtime = load(root, "enterprise/services/source/runtime_sites_2026-09-11.json")["sites"]
        land = next(s for s in runtime if s["id"] == "RUNTIME-NN-OWNED-DC")
        table_value(
            "land", "Accepted fictional land consideration", land["planning_consideration_usd"]
        )
        table_value(
            "tax-billing",
            "Released invoice amount",
            load(root, "docs/finance/evidence/SH-FIN-HUMAN-001/source.json")["rows"]["invoices"][0][
                "amount_usd"
            ],
        )
        # Relational ownership: every accepted subsidiary must keep its exact immediate parent.
        formation_rows = {
            r[0]: r
            for r in markdown_rows(texts["formations"])
            if r and r[0] in {e["entity_id"] for e in entities["entities"]}
        }
        for entity in entities["entities"]:
            if entity["entity_id"] == "NMI":
                continue
            r = formation_rows[entity["entity_id"]]
            equal(r[1], entity["legal_name"], f"formation legal identity {entity['entity_id']}")
            if entity["owner_entity_id"]:
                equal(
                    r[3],
                    f"{entity['owner_entity_id']}, {entity['ownership_percent']}%",
                    f"formation immediate owner {entity['entity_id']}",
                )

        # Structured companions must agree too; Markdown checks cannot protect XLSX inputs.
        def schedule_amounts(slug, key, value, expected):
            selected = {r[key]: r[value] for r in rows(drafts[slug]) if key in r and value in r}
            for label, amount in expected.items():
                equal(selected.get(label), amount, f"{slug} JSON {label}")

        schedule_amounts(
            "debt-liens",
            "line",
            "amount_usd",
            {
                "Buyer share consideration": txn["buyer_consideration"],
                "Old term/revolver payoff": txn["existing_term_revolver_refinance"],
                "Total uses before fees": uses,
                "Total sources before fees": sources,
                "New term advance": txn["new_debt"],
                "Parent equity before fees": txn["parent_equity_before_fees"],
                "Transaction expense funding": txn["transaction_expense"],
                "Debt issuance cost funding": txn["debt_issuance_cost"],
                "Parent cash including fees": txn["parent_equity_before_fees"]
                + txn["transaction_expense"]
                + txn["debt_issuance_cost"],
            },
        )
        schedule_amounts(
            "tax-filing",
            "measure",
            "amount_usd",
            {
                "Stock consideration": txn["buyer_consideration"],
                "Recognized tax assumed liabilities": tax["recognized_assumed_liabilities_usd"],
                "Modeled adjusted grossed-up basis": tax["modeled_agub_usd"],
                "Other tax asset bases": sum(tax["other_tax_asset_bases_usd"].values()),
                "Tax goodwill": tax["tax_goodwill_basis_usd"],
                "Environmental/claim reserves": txn["environment_reserve"] + txn["claim_reserve"],
                "Conditional reserve DTA": bridge["deferred_tax_asset_usd"],
                "Identifiable book net assets": bridge[
                    "identifiable_net_assets_before_refinancing_usd"
                ],
                "Book goodwill": bridge["goodwill_usd"],
                "Initial book goodwill excess over tax": bridge[
                    "initial_book_goodwill_excess_over_tax_usd"
                ],
            },
        )
        investments = {r["instrument"]: r for r in rows(drafts["financing-documents"])}
        equal(investments["HV"]["financing_usd"], hv, "HV JSON approximate financing")
        equal(investments["WR"]["financing_usd"], wr, "WR JSON approximate financing")
        equal(investments["WR"]["post_money_usd"], post, "WR JSON approximate post-money")
        equal(
            investments["WR"]["implied_pre_money_usd"], post - wr, "WR implied pre-money arithmetic"
        )
        equal(
            number(investments["WR"]["derived_new_money_ratio_percent"]),
            wr / post * 100,
            "WR ratio not investor allocation",
        )
        equal(
            number(investments["WR"]["insiders_post_percent"])
            + number(investments["WR"]["outside_post_percent"]),
            Decimal(100),
            "rounded ownership sums to 100",
        )
        subsidiaries = {r["entity_id"]: r for r in rows(drafts["formations"]) if "entity_id" in r}
        for entity in entities["entities"]:
            if entity["entity_id"] == "NMI":
                continue
            row = subsidiaries[entity["entity_id"]]
            equal(row["company"], entity["legal_name"], f"JSON entity name {entity['entity_id']}")
            equal(
                row["ownership_percent"],
                entity["ownership_percent"],
                f"JSON ownership percent {entity['entity_id']}",
            )
            if entity["owner_entity_id"]:
                equal(
                    row["holder"], entity["owner_entity_id"], f"JSON parent {entity['entity_id']}"
                )
        seller_rows = {
            r["holder"]: r["ownership_percent"]
            for r in rows(drafts["formations"])
            if "holder" in r and "entity_id" not in r
        }
        equal(
            seller_rows,
            {r["name"]: r["percent"] for r in txn["stockholders"]},
            "four ARU sellers source equality",
        )
        schedule_amounts(
            "land",
            "measure",
            "amount_usd",
            {
                "Accepted fictional land consideration": land["planning_consideration_usd"],
                "Land settlement cash": None,
                "Settlement adjustments": None,
            },
        )
        land_postings = [r for r in rows(drafts["land"]) if "account_description" in r]
        equal(
            sum(r["debit_usd"] for r in land_postings),
            land["planning_consideration_usd"],
            "land debit once",
        )
        equal(
            sum(r["credit_usd"] for r in land_postings),
            land["planning_consideration_usd"],
            "land clearing credit once",
        )
        red_wash = load(root, "red_wash/source/core_operating_data.json")["transaction"]
        rw_expected = {
            "direct_seller_payment": red_wash["cash_consideration_usd"]
            - red_wash["environmental_title_escrow_usd"]
            - red_wash["holdback_usd"],
            "environmental_title_escrow": red_wash["environmental_title_escrow_usd"],
            "holdback": red_wash["holdback_usd"],
            "total": red_wash["cash_consideration_usd"],
        }
        schedule_amounts("rw-title", "component", "amount_usd", rw_expected)
        schedule_amounts(
            "rw-chronology",
            "measure",
            "amount_usd",
            {
                "cash_consideration": red_wash["cash_consideration_usd"],
                "environmental_title_escrow": red_wash["environmental_title_escrow_usd"],
                "holdback": red_wash["holdback_usd"],
                "transaction_debt": red_wash["transaction_debt_usd"],
                "goodwill": red_wash["goodwill_usd"],
            },
        )
        for row in rows(drafts["tax-billing"]):
            if row["field"] != "Released invoice":
                equal(row["amount_or_rate"], None, f"tax-billing {row['field']} not invented")

        # Source-bound dependency, not a local hash that silently approves changed proposal bytes.
        decision = load(root, "docs/legal/evidence/proposals/decision-register.json")[
            "billing_proposal_reference"
        ]
        dependency = root / PACKAGE / "dependencies/billing-proposal-PR138.json"
        equal(
            hashlib.sha256(dependency.read_bytes()).hexdigest(),
            decision["sha256"],
            "sole billing proposal hash",
        )
        proposal = json.loads(dependency.read_text())
        equal(
            proposal["acceptance"]["state"], "NOT_ACCEPTED", "billing proposal remains unaccepted"
        )
        packet = load(root, "docs/finance/evidence/SH-FIN-HUMAN-001/source.json")
        invoice = packet["rows"]["invoices"][0]
        equal(
            proposal["preserved_source_values"]["invoice"],
            invoice,
            "proposal preserves entire native invoice row",
        )
        expected_billing = {
            "Original invoice": number(invoice["amount_usd"]),
            "Collections including recovery": number(invoice["collected_usd"]),
            "Credits": number(invoice["credit_usd"]),
            "Ledger AR remaining": number(invoice["remaining_usd"]),
            "Surviving written-off claim": number(invoice["writtenoff_usd"])
            - number(invoice["writtenoff_credit_usd"])
            - number(invoice["recovered_usd"]),
        }
        equal(
            {r["measure"]: number(r["amount_usd"]) for r in rows(drafts["billing"])},
            expected_billing,
            "billing financial schedule equals native invoice",
        )
        for r in rows(drafts["colo"]):
            equal(
                number(r["quantity_kw"]) * number(r["rate_usd_per_kw_month"]),
                number(r["monthly_usd"]),
                f"colo {r['site']} {r['quantity_kw']}kW sensitivity",
            )
        # Preserve intentionally unresolved cash flows and rates.
        for slug, columns in {
            "host-rights": ["eligible_realized_value", "participation_rate", "host_amount"],
            "tenure": ["rent_usd", "purchase_price_usd", "commencement"],
            "uranium-custody": ["rate", "quantity", "liability_cap"],
        }.items():
            for index, r in enumerate(rows(drafts[slug])):
                for column in columns:
                    equal(r[column], None, f"{slug} row {index} {column} remains unresolved")
        with (root / "geospatial/registers/SITE_REGISTER.csv").open() as handle:
            sites = list(csv.DictReader(handle))
        site_ids = {r["object_id"] for r in sites}
        for r in rows(drafts["tenure"]):
            if r["site_id"] not in site_ids:
                errors.append(f"tenure unknown source site ID: {r['site_id']}")
            else:
                checks.append(f"tenure source site {r['site_id']}")
        # Compare exact named host site table entries against geographic register identities.
        geo = {r["object_id"]: r for r in sites}
        host_entries = [
            r
            for r in markdown_rows(texts["host-rights"])
            if r and r[0] == "Stable geographic record"
        ]
        equal(
            {r[1] for r in host_entries},
            {
                f"{site_id}, {geo[site_id]['canonical_name']}"
                for site_id in ["SH-SITE-0023", "SH-SITE-0027"]
            },
            "host exact site identities",
        )
        for site_id in ["SH-SITE-0023", "SH-SITE-0027"]:
            equal(
                geo[site_id]["object_type"],
                "HOST_PROCESS_SITE",
                f"{site_id} external host classification",
            )
        for site in runtime:
            if site["id"] in ["RUNTIME-RENO-COLO", "RUNTIME-BOISE-DR"]:
                equal(site["capacity_reserved"], False, f"{site['id']} source has no reservation")
                equal(site["contract_executed"], False, f"{site['id']} source unexecuted")
        equal(land["commissioned_it_kw"], 0, "owned land no commissioned IT")
    except (OSError, ValueError, TypeError, KeyError, StopIteration, ArithmeticError) as exc:
        errors.append(f"Missing or malformed reconciliation evidence: {exc}")
    return errors, checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    errors, checks = check(args.root)
    print(f"{'FAIL' if errors else 'PASS'}: {len(checks)} focused legal term/source checks")
    for error in errors:
        print(f"- {error}")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
