import pytest

from enterprise.closeout.reperform import compare_protected


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
