import unittest

from swarmcontext.personalization import Feedback, PolicySelector, approved_policies, demonstration
from swarmcontext.registry import ContractError


class PersonalizationTests(unittest.TestCase):
    def test_demo_is_deterministic_and_isolated(self):
        one = demonstration()
        self.assertEqual(one, demonstration())
        self.assertEqual(set(one["examples"]), {"consumer", "smb", "enterprise"})
        self.assertTrue(all(row["cross_tenant_excluded"] for row in one["examples"].values()))
        self.assertTrue(all(row["post_feedback_policy"] == "rich" for row in one["examples"].values()))

    def test_feedback_is_partitioned_and_restricted_to_approved_arms(self):
        selector = PolicySelector(approved_policies())
        selector.observe("consumer", "compact", Feedback(True, 0.02, 100))
        self.assertEqual(selector.snapshot()["smb"]["compact"]["observations"], 0)
        with self.assertRaises(ContractError):
            selector.observe("consumer", "unapproved", Feedback(True, 0, 0))
        with self.assertRaises(ContractError):
            selector.observe("consumer", "compact", Feedback(True, -1, 0))


if __name__ == "__main__":
    unittest.main()
