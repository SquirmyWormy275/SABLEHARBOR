from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RedWashRecordTests(unittest.TestCase):
    def test_core_identity_and_math(self) -> None:
        core = json.loads((ROOT / "data/core_operating_data.json").read_text(encoding="utf-8"))
        self.assertEqual(core["record_id"], "SH-PS-RW-TOR-001")
        self.assertEqual(core["mine_2026"]["ore_tons"], 175000)
        self.assertEqual(core["mine_2026"]["produced_u3o8_lb"], 547400)
        self.assertEqual(core["mine_2026"]["sold_u3o8_lb"], 500000)
        self.assertEqual(core["mine_2026"]["ending_finished_inventory_lb"], 172400)
        self.assertEqual(core["finance_2026"]["revenue_usd"], 36475000)
        self.assertEqual(core["workforce_2026"]["total_fte"], 140)

    def test_generated_package(self) -> None:
        subprocess.run([sys.executable, str(ROOT / "tools/build_red_wash_package.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "tools/validate_red_wash_record.py")], check=True)


if __name__ == "__main__":
    unittest.main()
