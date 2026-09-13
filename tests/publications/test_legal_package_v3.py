"""The addendum must preserve prior files and expose complete offline evidence."""

from pathlib import Path

import pytest

from tools.legal_gaps import package, package_v3


def test_extended_bundle_preserves_originals_and_contains_csvs(tmp_path):
    output = tmp_path / "review"
    before_version, before_collect = package.VERSION, package.collect
    package_v3.build(output, allow_dirty=True)
    manifest = package.verify(output)
    assert manifest["version"] == "0.3.0-review.1"
    assert package.VERSION == before_version and package.collect is before_collect
    for path in manifest["original_files"]:
        assert (output / path).read_bytes() == (package.ROOT / path).read_bytes()
    csvs = list((package.ROOT / package.PREFIX / "walkthroughs/source").glob("*.csv"))
    assert len(csvs) == 15
    for path in csvs:
        assert (output / path.relative_to(package.ROOT)).read_bytes() == path.read_bytes()
    start = (output / "START_HERE.html").read_text()
    for directory in ("walkthroughs", "reconciliations", "decision-import"):
        assert directory + "/README.md.html" in start
        assert (output / package.PREFIX / directory / "README.md.html").is_file()
    assert (output / package.PREFIX / "review.html").is_file()
    assert Path(str(output) + ".zip").is_file()


def test_existing_release_is_never_overwritten(tmp_path):
    output = tmp_path / "review"
    output.mkdir()
    (output / "keep").write_text("original")
    with pytest.raises(ValueError, match="never replace"):
        package_v3.build(output, allow_dirty=True)
    assert (output / "keep").read_text() == "original"
