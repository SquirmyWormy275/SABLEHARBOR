"""Keep the documented publication entry point aligned with the locked manifest (#204)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.company_closeout import publications as successor  # noqa: E402
from tools.documents import build_controlled_publications as predecessor  # noqa: E402

MANIFEST = ROOT / "docs/governance/publication_manifest.json"


class PublicationSuccessorPopulationTests(unittest.TestCase):
    def setUp(self) -> None:
        artifacts = json.loads(MANIFEST.read_text(encoding="utf-8"))["artifacts"]
        self.manifest = [(a["source"], a["publication"], a["brand"]) for a in artifacts]
        self.successor = [*predecessor.DOCS, *successor.COMPANY_DOCS]

    def test_successor_population_matches_locked_manifest_in_order(self) -> None:
        self.assertEqual(len(self.manifest), 148)
        self.assertEqual(self.successor, self.manifest)

    def test_predecessor_alone_omits_exactly_the_company_sources(self) -> None:
        self.assertEqual(len(predecessor.DOCS), 131)
        self.assertEqual(len(successor.COMPANY_DOCS), 17)
        self.assertEqual(self.manifest[: len(predecessor.DOCS)], list(predecessor.DOCS))
        self.assertEqual(self.manifest[len(predecessor.DOCS) :], successor.COMPANY_DOCS)

    def test_successor_restores_predecessor_population_after_run(self) -> None:
        original = predecessor.DOCS
        calls = []
        real_main = predecessor.main
        try:
            predecessor.main = lambda: calls.append(list(predecessor.DOCS))
            successor.main()
        finally:
            predecessor.main = real_main
        self.assertEqual(calls, [self.successor])
        self.assertIs(predecessor.DOCS, original)

    def test_maintainer_docs_name_the_successor_entry_point(self) -> None:
        command = "python -m tools.company_closeout.publications"
        for rel in ("MAINTAINERS.md", "tools/documents/README.md"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn(command, text, rel)
            self.assertNotIn("\npython tools/documents/build_controlled_publications.py", text, rel)


if __name__ == "__main__":
    unittest.main()
