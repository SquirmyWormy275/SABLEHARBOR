from pathlib import Path
from zipfile import ZipFile

from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Base
from sable_harbor.generation import generate_standard
from sable_harbor.provenance.service import complete_generation_run, record_generation_run
from sable_harbor.reporting_queries import run_named_query
from sable_harbor.workbooks.suite import (
    SHEET_SPECS,
    WORKBOOKS,
    generate_workbook_suite,
)


def test_six_workbooks_reopen_have_required_sheets_and_clean_links(tmp_path: Path) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = record_generation_run(
            session, profile="standard", scenario_code="base", seed=20260831, git_commit="test"
        )
        generate_standard(session)
        complete_generation_run(session, run)
        session.commit()
        expected_headers = {
            sheet: list(run_named_query(session, SHEET_SPECS[sheet].query, run.id)[0])
            for sheet in (
                "Monthly Consolidated P&L",
                "Monthly Balance Sheet",
                "Journal Detail Extract",
            )
        }
        outputs = generate_workbook_suite(session, tmp_path, generation_run_id=run.id)
    assert set(SHEET_SPECS) == {sheet for sheets in WORKBOOKS.values() for sheet in sheets}
    assert {path.name for path in outputs} == set(WORKBOOKS)
    for output in outputs:
        assert 5_000 < output.stat().st_size < 20_000_000
        with ZipFile(output) as archive:
            assert not any("externalLinks" in name for name in archive.namelist())
        workbook = load_workbook(output, read_only=False, data_only=False)
        assert workbook.sheetnames == WORKBOOKS[output.name]
        check_sheet = workbook["Checks"]
        formulas = [
            cell.value for row in check_sheet.iter_rows() for cell in row if cell.data_type == "f"
        ]
        assert formulas
        assert all("#REF!" not in formula for formula in formulas)
        assert any("ABS(" in formula and "<=0.01" in formula for formula in formulas)
        for sheet_name, headers in expected_headers.items():
            if sheet_name not in workbook.sheetnames:
                continue
            actual_headers = [cell.value for cell in workbook[sheet_name][7]]
            assert actual_headers[: len(headers)] == headers


def test_sheet_routing_uses_exact_registry_not_title_substrings() -> None:
    assert SHEET_SPECS["Monthly Balance Sheet"].query == "entity_trial_balance"
    assert SHEET_SPECS["Monthly Consolidated P&L"].query == "consolidated_monthly_pnl"
    assert SHEET_SPECS["Journal Detail Extract"].query == "journal_to_source_trace"
    assert SHEET_SPECS["Red Wash Production Inv"].query == "red_wash_unit_cost_bridge"
    assert SHEET_SPECS["ARU-BS&T Volume and Rates"].query == "aru_route_customer_margin"
    assert all(spec.purpose and spec.empty_state for spec in SHEET_SPECS.values())
