import unittest

from swarmcontext.evolution import graph_fixture


class EvolutionFixtureTest(unittest.TestCase):
    def test_graph_fixture_is_scoped_and_deletion_propagates(self):
        result = graph_fixture()
        self.assertEqual(result["source_recall"], 1.0)
        self.assertEqual(result["source_precision"], 1.0)
        self.assertEqual(result["forbidden_scope_leaks"], 0)
        self.assertEqual(result["deleted_records"], 1)
        self.assertFalse(result["deleted_source_reappeared"])
        self.assertEqual(result["claim"], "local_synthetic_contract_only")


if __name__ == "__main__":
    unittest.main()
