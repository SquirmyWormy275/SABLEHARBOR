"""Offline payload precision, dictionary and script-content boundaries."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from industrial.planning.browser import build


class BrowserTests(unittest.TestCase):
    def test_dictionary_roundtrip_preserves_identifiers_decimal_money_and_scenarios(self):
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            path = "industrial/generated/planning/forecast/example.csv"
            target = stage / path
            target.parent.mkdir(parents=True)
            rows = [["base", "2027", "001", "0.0001", "</script><script>alert(1)</script>"]] * 8
            with target.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["scenario", "year", "account", "amount_usd", "description"])
                writer.writerows(rows)
            result = build(stage, [{"path": path}], "a" * 40, "WORKING_TREE_DEVELOPMENT")
            script = (stage / "case_data.js").read_text()
            self.assertNotIn("</script>", script)
            payload = json.loads(script.removeprefix("window.SABLE_CASE=").removesuffix(";\n"))
            table = payload["tables"]["forecast/example"]
            for column, values in table["string_dictionaries"].items():
                for row in table["rows"]:
                    row[int(column)] = values[row[int(column)]]
            expected = [["base", 2027, "001", "0.0001", rows[0][-1]]] * 8
            self.assertEqual(table["rows"], expected)
            self.assertEqual(payload["scenarios"], ["base"])
            self.assertEqual(result["record_count"], 8)

    def test_empty_catalog_cannot_create_apparently_complete_browser(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "No planning datasets"):
                build(Path(temp), [], "a" * 40, "CLEAN_COMMIT")
