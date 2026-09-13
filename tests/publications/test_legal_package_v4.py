"""The successor exposes new case files without replacing prior review editions."""

import pytest

from tools.legal_gaps import package, package_v3, package_v4


def test_new_bundle_preserves_bytes_and_offline_routes(tmp_path):
    output = tmp_path / "review"
    old = (package_v3.VERSION, package_v3.ADDITIONS, package.VERSION, package.collect)
    package_v4.build(output, allow_dirty=True)
    assert old == (package_v3.VERSION, package_v3.ADDITIONS, package.VERSION, package.collect)
    manifest = package.verify(output)
    assert manifest["version"] == "0.4.0-review.2"
    for relative in manifest["original_files"]:
        assert (output / relative).read_bytes() == (package.ROOT / relative).read_bytes()
    assert not any("/qa/" in r["path"] for r in manifest["files"])
    assert not (output / "docs/internal/institutional_catalog.sqlite3").exists()
    start = (output / "START_HERE.html").read_text()
    for folder in package_v4.ADDITIONS:
        assert folder + "/README.md.html" in start
        assert (output / package.PREFIX / folder / "README.md.html").is_file()
    for source in (package.ROOT / package.PREFIX / "period-close/source").glob("*.csv"):
        assert (output / source.relative_to(package.ROOT)).read_bytes() == source.read_bytes()


def test_refuses_overwrite(tmp_path):
    output = tmp_path / "review"
    output.mkdir()
    with pytest.raises(ValueError, match="never replace"):
        package_v4.build(output)
