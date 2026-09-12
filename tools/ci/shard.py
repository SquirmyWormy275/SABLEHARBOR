"""Deterministically balance collected tests; each CI job has an isolated checkout."""

import json
import os
from pathlib import Path


def partition(nodeids, count, weights):
    if count < 1 or len(nodeids) != len(set(nodeids)):
        raise ValueError("Shard count must be positive and node IDs unique")
    buckets = [[] for _ in range(count)]
    totals = [0.0] * count
    for nodeid in sorted(nodeids, key=lambda key: (-weights.get(key, 1.0), key)):
        index = min(range(count), key=lambda i: (totals[i], i))
        buckets[index].append(nodeid)
        totals[index] += weights.get(nodeid, 1.0)
    return buckets


def pytest_collection_modifyitems(config, items):
    count = int(os.environ["SHFIN_TEST_SHARDS"])
    index = int(os.environ["SHFIN_TEST_SHARD"])
    if not 0 <= index < count:
        raise ValueError("Shard index outside configured range")
    weights = json.loads(Path(__file__).with_name("test_weights.json").read_text())
    selected = set(partition([item.nodeid for item in items], count, weights)[index])
    deselected = [item for item in items if item.nodeid not in selected]
    items[:] = [item for item in items if item.nodeid in selected]
    config.hook.pytest_deselected(items=deselected)
