"""One-off PR 167 edit script; remove after the checked changes are committed."""
from pathlib import Path
import json


def replace(path, old, new):
    file = Path(path)
    text = file.read_text()
    assert text.count(old) == 1, (path, old[:100], text.count(old))
    file.write_text(text.replace(old, new))


# Keep the source excerpts intact, but stop interrupting the article with them.
path = Path('tools/wiki/export.py')
text = path.read_text()
start = text.index('    def article(self, page: Path) -> str:')
end = text.index('    def reading_pages(self)', start)
text = text[:start] + '''    def article(self, page: Path) -> str:
        result = self.rewrite(page)
        entries = self.reading["articles"].get(page.relative_to(self.wiki).as_posix(), [])
        if entries:
            # Preserve the old section address and every excerpt. Reading the
            # business must not require reading its entire approval history.
            result += (
                "\\n## In-depth reading\\n\\n"
                "<!-- supporting-records:start -->\\n"
                "<details>\\n<summary>Supporting records and decision history</summary>\\n\\n"
                f"[Records and decisions](https://github.com/{REPOSITORY}/wiki/Records-and-Decisions)\\n\\n"
                "Original source text follows. Read each record's date and any later "
                "replacement alongside it.\\n\\n"
                + "\\n".join(self.excerpt(entry) for entry in entries)
                + "\\n</details>\\n<!-- supporting-records:end -->\\n"
            )
        return result

''' + text[end:]
old = '        tokens = MARKDOWN.parse(text)\n        for i, token in enumerate(tokens):'
new = '        # Keep the article contents short; source sections remain addressable\n        # inside the optional appendix and on their full reading pages.\n        primary = text.split("<!-- supporting-records:start -->", 1)[0]\n        tokens = MARKDOWN.parse(primary)\n        for i, token in enumerate(tokens):'
assert text.count(old) == 1
text = text.replace(old, new)
old = '''            "Source wording follows. Its dates, qualifications and supersession scope apply; "
            "this reading edition does not resolve open decisions.\\n\\n" + body + "\\n"
'''
new = '''            + body + "\\n"
'''
assert text.count(old) == 1
text = text.replace(old, new)
old = '            "- [Document library](Library)",'
new = '            "- [Locations and facilities](Locations)",\n            "- [Document library](Library)",\n            "- [Records and decisions](Records-and-Decisions)",'
assert text.count(old) == 1
text = text.replace(old, new)
old = '                "[Open questions](Open-Questions)\\n"'
new = '                "[Records and decisions](Records-and-Decisions) · "\n                "[Open questions](Open-Questions)\\n"'
assert text.count(old) == 1
text = text.replace(old, new)
path.write_text(text)
compile(text, str(path), 'exec')

# Only exact, redundant stock sentences are removed across the subject guides.
# Operating restrictions, unknowns, numbers, quotations and source text remain.
boilerplate = {
    '**Reviewed:** September 12, 2026 · Fictional enterprise; source records control.\n\n': '',
    'Related reading describes useful connections, not additional reporting lines.\n': '',
    'Read the chart’s text roster, relationship key and source qualifications': 'Chart and text roster',
    '. Grouped functions are not automatically reporting lines, separate companies or additional employees.': '.',
    ' — the current chart preserves unknown joining years rather than inventing them.': '.',
}
changed_guides = []
for directory in ('businesses', 'departments', 'subjects'):
    for file in sorted(Path('docs/wiki', directory).glob('*.md')):
        original = file.read_text()
        updated = original
        for old, new in boilerplate.items():
            updated = updated.replace(old, new)
        if updated != original:
            file.write_text(updated.rstrip() + '\n')
            changed_guides.append(str(file))
print('Exact boilerplate cleanup:', json.dumps(changed_guides))

replace('docs/wiki/businesses/Foundry-Field.md',
    'It is a commercial product business recorded on the parent’s SHI books. A dedicated working base is unresolved; the Sacramento product floor is a proposed campus allocation, not proof of current occupancy.',
    'Foundry Field is recorded on the parent’s SHI books. Its team uses shared offices in Reno and Sacramento, alongside customer-embedded and mobile field work. The Sacramento product-floor drawing is a fit-out proposal, not an additional completed facility. See the [location directory](../Locations.md) for the current working bases.')
replace('docs/wiki/businesses/Atlas-Meridian.md',
    'Atlas is a parent-book product business, distinct from Advisory, J2 and the geographic atlas. A dedicated physical working base remains unresolved.',
    'Atlas is recorded on the parent’s books and remains distinct from Advisory, J2 and the geographic atlas. It uses shared accommodation in Tucson and Sacramento, with deployed work through the existing business teams. See the [location directory](../Locations.md).')
replace('docs/wiki/businesses/Atlas-Meridian.md',
    '| [September 9 decisions](../../../docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-09_ADVISORY_TIER1.md) | Use ATL-201–209 for current commercial direction; these supersede older open pricing and edition wording. |\n',
    '')
replace('docs/wiki/businesses/Pale-Sun-Red-Wash.md',
    'The legal chain is Sable Harbor → Sable Harbor Industrial Holdings → Pale Sun → Red Wash Mining. RWH is a stable reporting code, not the name “Red Wash Holdings.” Pale Sun’s own office location is not established by the mine’s geography.',
    'Pale Sun belongs to Sable Harbor Industrial Holdings and owns Red Wash Mining. Its mining operation is in the Great Divide Basin / Red Desert, north of Wamsutter in Sweetwater County, Wyoming. The [location directory](../Locations.md) distinguishes the operating sites from offices and proposed facilities. In the accounting records, RWH is the reporting code for Red Wash Mining.')
replace('docs/wiki/businesses/Pale-Sun-Red-Wash.md',
    '## Places and plans\n\n',
    '## Places and plans\n\nRed Wash is the Wyoming operating site, not an unknown location. The older Carbon County siting has been replaced by Sweetwater County. A separate Pale Sun office address is discussed in the [supporting location notes](../Records-and-Decisions.md#locations).\n\n')

replace('docs/wiki/Home.md',
    '**Reviewed:** September 12, 2026 · **Status:** reader\'s guide; the linked source records remain authoritative.\n\n', '')
replace('docs/wiki/Home.md',
    'Business, department, and history articles include the supporting source text, so you can follow the details without leaving the Wiki.',
    'Each article explains the subject first. Supporting records are available at the end when you need to inspect them.')
replace('docs/wiki/Home.md',
    'Choose a business or department below. Its **In-depth reading** section contains the detailed operating, authority, or history records. Use **On this page** to move through a long article. The [full-text reading room](https://github.com/SquirmyWormy275/SABLEHARBOR/wiki/Reading) collects 198 supporting records, each linked to the repository version used for publication. The [start guide](Start-Here.md) explains the downloads and document status labels.',
    'Choose a business or department below. Use **On this page** to move through an article. The optional **Supporting records and decision history** section at the end contains the original documents; the [records guide](Records-and-Decisions.md) brings the decision history together in one place. The [start guide](Start-Here.md) explains the downloads.')
replace('docs/wiki/Home.md',
    '- [Locations and facilities](../../geospatial/facilities/README.md) — Context maps, site plans, buildings, and floors, with their status and supporting evidence.',
    '- [Locations and facilities](Locations.md) — Offices, operating sites, shared accommodation, maps and floor plans.')
replace('docs/wiki/Home.md',
    '- [Corporate history and canon files](library/history.md) — Dated decisions, including notes on which later decisions replace them.',
    '- [Records and decisions](Records-and-Decisions.md) — Supporting sources, approval history and the decisions that replaced older records.')

replace('CONTRIBUTING.md',
    'Before submitting, read the changed passages aloud.',
    'Keep the company explanation separate from its design history. State the current fact directly; put approval codes, supersession chains and detailed provenance in the existing registers, reached through [Records and decisions](docs/wiki/Records-and-Decisions.md). A useful source link is not a requirement to repeat the whole chain. Keep qualifications that matter to accounting, control testing or operations next to the relevant claim.\n\nBefore copying an “unknown” location, check later decisions. Distinguish a business’s office from its operating site, incorporation jurisdiction and proposed facilities. Record the city or shared accommodation that is known without inventing a street address.\n\nBefore submitting, read the changed passages aloud.')
replace('docs/reader/SOURCES_AND_FORMATS.md',
    '## Read the company, then inspect the evidence\n\n',
    '## Read the company, then inspect the evidence\n\n[Records and decisions](../wiki/Records-and-Decisions.md) is the central guide to source authority and change history. Ordinary business articles explain the company without repeating that history.\n\n')
replace('docs/organization/README.md',
    '**40 chart families · 57 pages · Revision 1.1.0 · September 10, 2026**\n\n',
    '**40 chart families · 57 pages · Revision 1.1.0 · September 10, 2026**\n\nFor current office and operating locations, use the [location directory](../wiki/Locations.md). The later accommodation decisions place Foundry Field across Reno and Sacramento and Atlas Meridian across Tucson and Sacramento; their unrecorded-location labels in this dated chart edition are stale. Pale Sun’s Red Wash mine is in Sweetwater County, Wyoming. The [supporting notes](../wiki/Records-and-Decisions.md#locations) distinguish that mine from a separate Pale Sun office.\n\n')
replace('geospatial/README.md',
    '# Sable Harbor geospatial framework\n\n',
    '# Sable Harbor geospatial framework\n\n[Current locations](../docs/wiki/Locations.md) describes the offices and operating sites. For the decisions behind the maps, use [Records and decisions](../docs/wiki/Records-and-Decisions.md#locations). The package editions below retain their own dates and scope.\n\n')
replace('geospatial/README.md',
    '- Bedford: Fairmont-area Cradle center, 15–20 acres; exact parcel unfinished. Belle/Kanawha is historical editorial siting, not an operating site or relocation.',
    '- Bedford: Cradle’s Fairmont / White Hall-area center. The September 13 decision selects a 15.27-acre fictional redevelopment footprint. Belle/Kanawha is historical siting, not a current operation; the selected footprint is not a real property conveyance.')
replace('geospatial/README.md',
    "- The Fort: Willow's Pittsburgh-area 10–20 acre compound, with Big Shed research, Small Shed administration/temporary lodging, White Shed controlled intake/storage and the Museum working yard. Klein is the historical precursor. Exact shop/Fort occupancy linkage remains open.",
    '- The Fort: Willow’s Hazelwood, Pittsburgh compound, with Big Shed research, Small Shed administration/temporary lodging, White Shed intake/storage and the Museum working yard. The September 13 decision selects a 10.65-acre fictional footprint and preserves the staged 2024 move. The earlier Klein shop remains a distinct historical premise.')

# Keep these implementation notes in the tooling guide, not in every article.
file = Path('tools/wiki/README.md')
file.write_text(file.read_text().rstrip() + '''

## Reader-facing articles and supporting records

Business and department explanations come first. The exporter appends their original
source excerpts inside a closed “Supporting records and decision history” section.
It retains the `in-depth-reading` address, source-section addresses, complete source
text and the separate full-text reading pages. The article contents menu lists the
article sections rather than reproducing the source records' entire contents.

The Wiki sidebar and footer link to `Records-and-Decisions`; the sidebar also links
to `Locations`. The former indexes existing authority and history records instead
of creating a second decision register. Material operational and accounting limits
stay in the articles. Source records are not rewritten to make them shorter.
''')

file = Path('tests/test_wiki_reader_layout.py')
assert not file.exists()
file.write_text('''"""The reader can inspect every source without it interrupting the article."""
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
        assert "<details>\\n<summary>Supporting records and decision history</summary>" in composed
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
''')
compile(file.read_text(), str(file), 'exec')
print('Reader presentation and supported locations updated; original source records untouched.')
