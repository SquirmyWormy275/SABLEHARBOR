from tools.ci.shard import partition


def test_shards_preserve_every_test_including_new_tests():
    nodes = ["slow", "medium", "new", "new[param]", "fast"]
    shards = partition(nodes, 3, {"slow": 9, "medium": 5, "fast": 0.1})
    assert sorted(node for shard in shards for node in shard) == sorted(nodes)
    assert partition(list(reversed(nodes)), 3, {"slow": 9, "medium": 5, "fast": 0.1}) == shards
    assert shards[0] == ["slow"]
