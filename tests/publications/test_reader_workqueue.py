"""Reject unsafe task graphs and drift in explicitly frozen review assets."""

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "reader_workqueue", ROOT / "scripts/validate_reader_workqueue.py"
)
queue_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue_module)


class WorkqueueTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(queue_module.QUEUE.read_text())

    def test_current_queue(self):
        queue_module.validate(ROOT, self.data)

    def test_rejects_cycle_unknown_and_duplicate(self):
        for change in ("cycle", "unknown", "duplicate"):
            with self.subTest(change=change):
                data = copy.deepcopy(self.data)
                if change == "cycle":
                    data["jobs"][0]["depends_on"] = [data["jobs"][0]["id"]]
                elif change == "unknown":
                    data["jobs"][0]["depends_on"] = ["ABSENT"]
                else:
                    data["jobs"].append(data["jobs"][0])
                with self.assertRaises(ValueError):
                    queue_module.validate(ROOT, data)

    def test_rejects_cross_lane_write_collision(self):
        data = copy.deepcopy(self.data)
        data["jobs"][1]["write_scope"] = data["jobs"][0]["write_scope"]
        with self.assertRaisesRegex(ValueError, "Cross-lane write collision"):
            queue_module.validate(ROOT, data)

    def test_rejects_escaped_paths_and_frozen_drift(self):
        for change in ("path", "hash"):
            with self.subTest(change=change):
                data = copy.deepcopy(self.data)
                if change == "path":
                    data["jobs"][0]["write_scope"] = ["../outside"]
                else:
                    data["frozen"][0]["sha256"] = "0" * 64
                with self.assertRaises(ValueError):
                    queue_module.validate(ROOT, data)
