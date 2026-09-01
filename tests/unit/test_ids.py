from sable_harbor.core.ids import stable_id


def test_stable_id_is_deterministic() -> None:
    assert stable_id("entity", "SH") == stable_id("entity", "SH")
    assert stable_id("entity", "SH") != stable_id("account", "SH")
