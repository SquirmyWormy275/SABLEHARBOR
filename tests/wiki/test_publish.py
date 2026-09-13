import unittest

from tools.wiki.publish import check_source


class SourceGuardTests(unittest.TestCase):
    def test_dirty_or_unaccepted_source_is_rejected(self):
        for head, accepted, status in [("branch", "main", ""), ("main", "main", " M Home.md")]:
            with self.assertRaises(ValueError):
                check_source(head, accepted, status)
        check_source("main", "main", "")
