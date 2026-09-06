"""Controlled finance publications must not discard fenced reconciliation text."""

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools/documents/build_controlled_publications.py"
SPEC = importlib.util.spec_from_file_location("industrial_publications", SCRIPT)
publication = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publication)


class FinancialPublicationTests(unittest.TestCase):
    def test_fenced_financial_bridge_is_present_and_escaped(self):
        result = publication.body(
            "# Funding\n\n```text\nOpening ARO   16,467,716\n"
            "Cash < liability\n```\n\nEquity funds the deficit.\n"
        )
        self.assertIn("Opening ARO   16,467,716", result)
        self.assertIn("Cash &lt; liability", result)
        self.assertIn("Equity funds the deficit.", result)
        self.assertIn("<pre", result)


if __name__ == "__main__":
    unittest.main()
