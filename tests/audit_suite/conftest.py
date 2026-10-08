"""Keep historical private replay inputs separate from portable unit fixtures."""

import json
import os
from pathlib import Path

import pytest


def pytest_collection_modifyitems(items):
    selected = json.loads(Path(__file__).with_name("private_replay_modules.json").read_bytes())
    historical = set(selected["modules"])
    enabled = os.environ.get("SABLEHARBOR_RUN_PRIVATE_REPLAYS") == "1"
    private_root = os.environ.get("SABLEHARBOR_PRIVATE_REPLAY_ROOT")
    for item in items:
        if Path(str(item.path)).name not in historical:
            continue
        item.add_marker(pytest.mark.private_replay)
        if not enabled:
            item.add_marker(
                pytest.mark.skip(reason="Historical replay requires preserved private run inputs")
            )
        elif private_root:
            for name in ("PRIVATE", "PRIVATE_REPOSITORY"):
                if hasattr(item.module, name):
                    setattr(item.module, name, Path(private_root).resolve())
