"""The reader can inspect every source without it interrupting the article."""
from pathlib import Path

import pytest

from tools.wiki.audit import Page
from tools.wiki.export import Exporter

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def exporter():
    return Exporter(ROOT, "0" * 40)


def test_sources_follow_the_article_in_a_closed_appendix(exporter):
    for relative, entries in exporter.reading["articles"].items():
        article = ROOT / "docs/wiki" / relative
        primary = exporter.rewrite(article)
        composed = exporter.article(article)
        assert composed.startswith(primary)
        assert "<details>\n<summary>Supporting records and decision history</summary>" in composed
        assert "<details open" not in composed
        assert composed.index("<!-- supporting-records:start -->") >= len(primary)
        for entry in entries:
            assert exporter.excerpt(entry) in composed
        assert "in-depth-reading" in Page(composed).anchors


def test_primary_contents_do_not_repeat_source_section_lists(exporter):
    article = ROOT / "docs/wiki/businesses/Pale-Sun-Red-Wash.md"
    rendered = exporter.contents(exporter.article(article))
    menu = rendered.split("<summary>On this page</summary>", 1)[1].split("</details>", 1)[0]
    assert "In-depth reading" in menu
    assert "Source:" not in menu


def test_full_reading_editions_keep_the_original_source_text(exporter):
    editions = exporter.reading_pages()
    for source in exporter.records:
        assert exporter.rewrite(source) in editions[exporter.names[source] + ".md"]


def test_current_location_guides_do_not_revert_to_unknown():
    pages = ROOT / "docs/wiki/businesses"
    foundry = (pages / "Foundry-Field.md").read_text()
    atlas = (pages / "Atlas-Meridian.md").read_text()
    pale = (pages / "Pale-Sun-Red-Wash.md").read_text()
    assert "Reno and Sacramento" in foundry
    assert "Tucson and Sacramento" in atlas
    assert "Sweetwater County, Wyoming" in pale
    assert "A dedicated working base is unresolved" not in foundry
    assert "A dedicated physical working base remains unresolved" not in atlas
    # Mine geography must never be used to invent a Pale Sun office address.
    notes = (ROOT / "docs/wiki/Records-and-Decisions.md").read_text()
    assert "No accepted separate-office location was identified" in notes
