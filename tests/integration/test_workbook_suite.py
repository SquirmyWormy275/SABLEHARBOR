from pathlib import Path
from zipfile import ZipFile

from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sable_harbor.accounting.models import Base
from sable_harbor.generation import generate_standard
from sable_harbor.workbooks.suite import WORKBOOKS, generate_workbook_suite


def test_six_workbooks_reopen_have_required_sheets_and_clean_links(tmp_path: Path) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        generate_standard(session)
        session.commit()
        outputs = generate_workbook_suite(session, tmp_path)
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
