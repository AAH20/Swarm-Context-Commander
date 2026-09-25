import unittest

from swarmcontext.mcp_server import compile_context, recommend_placement
from swarmcontext.registry import ContractError


class MCPToolsTest(unittest.TestCase):
    def test_context_is_bounded_and_source_linked(self):
        result = compile_context("refund", [
            {"text": "Refund review is pending.", "source_id": "a"},
            {"text": "Unrelated ledger data.", "source_id": "b"},
        ], token_budget=20)
        self.assertEqual([x["memory_id"] for x in result["items"]], ["input-0"])
        self.assertEqual(result["input_record_count"], 2)
        self.assertEqual(len(result["items"][0]["source_sha256"]), 64)

    def test_rejects_oversize_and_unknown_fields(self):
        with self.assertRaises(ContractError):
            compile_context("x", [{"text": "a", "role": "system"}])
        with self.assertRaises(ContractError):
            compile_context("x", [{"text": "a"}] * 65)

    def test_placement_is_classification_only(self):
        self.assertEqual(recommend_placement(estimated_tokens=50)["placement"], "serverless")
        self.assertEqual(recommend_placement(estimated_tokens=50, needs_browser=True)["placement"], "container")
        self.assertEqual(recommend_placement(estimated_tokens=50, runs_code=True)["placement"], "microvm")
        with self.assertRaises(ContractError):
            recommend_placement(estimated_tokens=True)


if __name__ == "__main__":
    unittest.main()
