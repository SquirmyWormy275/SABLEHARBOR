"""Protect readable publication content when Markdown source lines are reflowed."""

from __future__ import annotations

import importlib.util
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "publication_builder", ROOT / "tools/documents/build_controlled_publications.py"
)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class PublicationContent(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.blocks: list[str] = []
        self.cells: list[tuple[str, dict[str, str | None]]] = []
        self.links: list[str | None] = []
        self._text: list[str] = []
        self._cell_attributes: dict[str, str | None] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.links.append(dict(attrs).get("href"))
        if tag in {"p", "li", "th", "td"}:
            self._text = []
        if tag in {"th", "td"}:
            self._cell_attributes = dict(attrs)
        if tag == "br":
            self._text.append("\n")

    def handle_data(self, data: str) -> None:
        self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "li"}:
            self.blocks.append("".join(self._text))
            self._text = []
        if tag in {"th", "td"} and self._cell_attributes is not None:
            self.cells.append(("".join(self._text), self._cell_attributes))
            self._cell_attributes = None
            self._text = []


def render_content(markdown: str) -> PublicationContent:
    content = PublicationContent()
    content.feed(BUILDER.body(markdown))
    content.close()
    return content


class PublicationMarkdownTests(unittest.TestCase):
    def test_publication_links_resolve_from_source_location(self) -> None:
        source_url = (
            "https://github.com/SquirmyWormy275/SABLEHARBOR/blob/main/"
            "docs/governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md"
        )
        content = PublicationContent()
        content.feed(
            BUILDER.body(
                "[Decision](../canon/DECISION_REGISTER_ADDENDUM_2026-09-06_CLOSEOUT.md)\n"
                "[Local section](#delivery) and [External](https://example.org/evidence).\n",
                source_url=source_url,
            )
        )
        content.close()
        self.assertEqual(
            content.links,
            [
                "https://github.com/SquirmyWormy275/SABLEHARBOR/blob/main/"
                "docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-06_CLOSEOUT.md",
                source_url + "#delivery",
                "https://example.org/evidence",
            ],
        )

    def test_source_reflow_keeps_one_readable_paragraph(self) -> None:
        content = render_content(
            "A record keeps its **provenance**\n"
            "across wrapped source lines.\n\n"
            "A separate paragraph remains separate.\n"
        )
        self.assertEqual(
            content.blocks,
            [
                "A record keeps its provenance across wrapped source lines.",
                "A separate paragraph remains separate.",
            ],
        )

    def test_explicit_hard_break_is_not_collapsed_into_running_text(self) -> None:
        content = render_content("Owner: J2  \nState: LOCKED\n")
        self.assertEqual("\n".join(content.blocks), "Owner: J2\nState: LOCKED")

    def test_wrapped_list_item_retains_its_continuation_and_item_boundary(self) -> None:
        content = render_content(
            "- Preserve stable IDs\n"
            "  and retain prior states.\n"
            "- Keep the next item separate.\n\n"
            "Outside the list.\n"
        )
        self.assertEqual(len(content.blocks), 3)
        self.assertTrue(content.blocks[0].endswith("Preserve stable IDs and retain prior states."))
        self.assertTrue(content.blocks[1].endswith("Keep the next item separate."))
        self.assertEqual(content.blocks[2], "Outside the list.")

    def test_short_table_identifiers_stay_intact_while_explanations_can_wrap(self) -> None:
        explanation = "Retain the original dated source and its complete provenance."
        content = render_content(
            "| Decision | State | Explanation |\n"
            "|---|---|---|\n"
            f"| CLOSE-001 | LOCKED | {explanation} |\n"
        )
        cells = dict(content.cells)
        self.assertEqual(
            set(cells), {"Decision", "State", "Explanation", "CLOSE-001", "LOCKED", explanation}
        )
        for label in ("CLOSE-001", "LOCKED"):
            attributes = cells[label]
            self.assertTrue(
                "nowrap" in attributes
                or "white-space:nowrap" in (attributes.get("style") or "").replace(" ", ""),
                f"Short publication identifier {label!r} can wrap inside its table column",
            )
        self.assertNotIn("nowrap", cells[explanation])
