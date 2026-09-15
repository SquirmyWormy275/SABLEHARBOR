from decimal import Decimal

import pytest

from enterprise.closeout.reperform import compare_protected, retention_closed_predecessor


def row(account="1600", amount="14762500.0000", source="ARU-ACQUISITION"):
    return dict(
        scenario="base",
        entity="ARU",
        year="2026",
        month="0",
        account=account,
        signed_usd=amount,
        source_id=source,
    )


def test_exact_acquisition_and_carryforward_population_preserved():
    source = [row(), row("3000", "-14762500", "OPENING-CARRY")]
    assert compare_protected(source, [row(amount="14762500"), source[1]]) == 2
    with pytest.raises(ValueError, match="added="):
        compare_protected([source[0], row("3000", "-14762499", "OPENING-CARRY")], source)
    with pytest.raises(ValueError):
        compare_protected(source + [source[0]], source)


def closing_population():
    result = [row()]
    for scenario in ("base", "downside", "expansion"):
        for entity in ("ARU", "BST"):
            for account, value in (("5000", "-100000"), ("3100", "20000")):
                result.append(
                    dict(
                        row(account, value, "CLOSE-2026-CORPORATE"),
                        scenario=scenario,
                        entity=entity,
                        year="2027",
                    )
                )
    return result


def test_retention_closes_expense_once_without_changing_acquisition():
    source = closing_population()
    expected = retention_closed_predecessor(
        source, {"ARU": Decimal("16065"), "BST": Decimal("8201.75")}
    )
    assert expected[0] == source[0]
    assert source[1]["signed_usd"] == "-100000"
    assert [r["signed_usd"] for r in expected[1:5]] == [
        "-116065",
        "36065",
        "-108201.75",
        "28201.75",
    ]
    assert compare_protected(expected, expected) == 13
    for index in (0, 1, 2, 3):
        corrupted = [dict(r) for r in expected]
        corrupted[index]["signed_usd"] = str(Decimal(corrupted[index]["signed_usd"]) + 1)
        with pytest.raises(ValueError, match="protected legal population changed"):
            compare_protected(corrupted, expected)
    wrong_year = [dict(r) for r in expected]
    wrong_year[1]["year"] = "2028"
    with pytest.raises(ValueError):
        compare_protected(wrong_year, expected)
    with pytest.raises(ValueError):
        compare_protected(expected + [expected[1]], expected)


@pytest.mark.parametrize("duplicate", [False, True])
def test_retention_reconstruction_rejects_incomplete_or_duplicate_closing_population(duplicate):
    source = closing_population()
    source = source + [source[1]] if duplicate else source[:1] + source[2:]
    with pytest.raises(ValueError, match="predecessor retention closing leg"):
        retention_closed_predecessor(source, {"ARU": Decimal("16065"), "BST": Decimal("8201.75")})
