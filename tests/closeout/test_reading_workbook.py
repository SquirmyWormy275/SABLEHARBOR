import pytest
from openpyxl import load_workbook

from enterprise.closeout import workbook


def test_readback_preserves_money_and_untrusted_literal(tmp_path, monkeypatch):
    monkeypatch.setattr(workbook, "SHEETS", [("Example", "source.csv", ["identity", "amount_usd"])])
    (tmp_path / "source.csv").write_text("identity,amount_usd\n=1+1,13325751.3907\n")
    receipt = workbook.build(tmp_path)
    assert receipt["independent_cell_readback_count"] == 2
    book = load_workbook(tmp_path / receipt["workbook"])
    assert book["Example"]["A6"].value == "=1+1"
    assert book["Example"]["A6"].data_type == "s"
    assert book["Example"]["B6"].value == 13325751.3907
    book.close()


def test_stale_workbook_input_schema_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(workbook, "SHEETS", [("Example", "source.csv", ["identity", "amount_usd"])])
    (tmp_path / "source.csv").write_text("identity\nA\n")
    with pytest.raises(ValueError, match="schema/population"):
        workbook.build(tmp_path)
