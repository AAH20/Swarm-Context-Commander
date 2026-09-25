import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from swarmcontext.benchmark import benchmark_fleet
from swarmcontext.cli import demo
from swarmcontext.context import ContextIndex, ContextPolicy, Memory
from swarmcontext.inference import InferenceRequest, TokenAdmission, batch_key, cache_salt, local_vllm_chat
from swarmcontext.protocol import cognee_chunks, computer_use_event, task_envelope
from swarmcontext.registry import ContractError, Registry
from swarmcontext.scheduler import FairQueue, Work, placement


class RegistryTests(unittest.TestCase):
    def test_idempotency_tenant_boundary_and_lease_fencing(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Registry(Path(folder) / "a.db")
            self.addCleanup(db.close)
            db.register("a", "tenant-a")
            db.register("b", "tenant-b")
            self.assertEqual(db.submit(task_id="task", agent_id="a", tenant_id="tenant-a",
                                       idempotency_key="one", request={"x": 1}), "task")
            self.assertEqual(db.submit(task_id="second", agent_id="a", tenant_id="tenant-a",
                                       idempotency_key="one", request={"x": 1}), "task")
            with self.assertRaisesRegex(ContractError, "different request"):
                db.submit(task_id="third", agent_id="a", tenant_id="tenant-a",
                          idempotency_key="one", request={"x": 2})
            with self.assertRaisesRegex(ContractError, "another tenant"):
                db.submit(task_id="bad", agent_id="b", tenant_id="tenant-a",
                          idempotency_key="two", request={})
            attempt = db.lease("task", "worker")
            with self.assertRaisesRegex(ContractError, "not available"):
                db.lease("task", "other")
            with self.assertRaisesRegex(ContractError, "stale"):
                db.finish("task", "other", attempt, success=True)
            db.finish("task", "worker", attempt, success=True)
            self.assertEqual(db.task_state("task"), "completed")

    def test_synthetic_registration_is_explicitly_logical(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Registry(Path(folder) / "fleet.db")
            self.assertEqual(db.register_synthetic(1000, tenants=10), 1000)
            db.close()


class ContextTests(unittest.TestCase):
    def test_scope_budget_graph_gc_and_tombstone(self):
        index = ContextIndex()
        source_a = hashlib.sha256(b"a").hexdigest()
        source_b = hashlib.sha256(b"b").hexdigest()
        source_secret = hashlib.sha256(b"secret").hexdigest()
        index.add(Memory("alice:a", "one", "agent", "Refund policy needs approval", source_a, 1,
                         trust=3, owner_agent_id="alice"))
        index.add(Memory("alice:b", "one", "tenant", "Ledger correction follows refund", source_b, 2, expires_at=3))
        index.add(Memory("bob:s", "two", "tenant", "Refund secret of another tenant", source_secret, 2))
        index.link("alice:a", "alice:b")
        with self.assertRaisesRegex(ContractError, "cross-tenant"):
            index.link("alice:a", "bob:s")
        bundle = index.compile("refund", tenant="one", agent="alice", now=2, token_budget=100)
        self.assertEqual(len(bundle["items"]), 2)
        self.assertNotIn("secret", str(bundle))
        self.assertEqual(index.collect_expired(3), 1)
        self.assertEqual(index.delete_source(source_a), 1)
        with self.assertRaisesRegex(ContractError, "cannot be reingested"):
            index.add(Memory("alice:new", "one", "tenant", "refund", source_a, 4))
        self.assertEqual(index.compile("refund", tenant="one", agent="alice", now=4)["items"], [])

    def test_agent_scoped_memory_is_not_retrieved_by_peer(self):
        index = ContextIndex()
        index.add(Memory("alice:private", "one", "agent", "Special refund fact", "a" * 64, 1,
                         owner_agent_id="alice"))
        self.assertEqual(index.compile("refund", tenant="one", agent="bob", now=2)["items"], [])

    def test_personal_policy_can_narrow_retrieval_and_versions_bundle(self):
        index = ContextIndex()
        index.add(Memory("low", "one", "tenant", "Refund note", "a" * 64, 1, trust=0))
        index.add(Memory("high", "one", "tenant", "Refund ledger", "b" * 64, 1, trust=3))
        policy = ContextPolicy(version="customer-3", min_trust=2, preferred_terms=("ledger",))
        result = index.compile("refund", tenant="one", agent="alice", now=2, policy=policy)
        self.assertEqual([item["memory_id"] for item in result["items"]], ["high"])
        self.assertEqual(result["policy_version"], "customer-3")


class SchedulerTests(unittest.TestCase):
    def test_fairness_and_placement(self):
        queue = FairQueue(quantum_tokens=100, max_tokens_per_work=1000)
        queue.put(Work("a1", "a", 100))
        queue.put(Work("a2", "a", 100))
        queue.put(Work("b1", "b", 100))
        self.assertEqual([queue.pop().task_id for _ in range(3)], ["a1", "b1", "a2"])
        self.assertEqual(placement(Work("x", "a", 10)), "serverless")
        self.assertEqual(placement(Work("x", "a", 10, needs_browser=True)), "container")
        self.assertEqual(placement(Work("x", "a", 10, runs_code=True)), "microvm")
        with self.assertRaisesRegex(ContractError, "bounds"):
            queue.put(Work("huge", "a", 1001))

    def test_large_task_accumulates_deficit(self):
        queue = FairQueue(quantum_tokens=100, max_tokens_per_work=1000)
        queue.put(Work("big", "one", 900))
        self.assertEqual(queue.pop().task_id, "big")


class InferenceAndProtocolTests(unittest.TestCase):
    def test_token_reservation_and_tenant_salt(self):
        pool = TokenAdmission(global_limit=200, tenant_limit=120)
        item = InferenceRequest("one", "a", "model", "p1", "a" * 64, 60, 40)
        second = InferenceRequest("two", "a", "model", "p1", "a" * 64, 60, 40)
        self.assertTrue(pool.admit(item))
        self.assertFalse(pool.admit(second))
        self.assertNotEqual(cache_salt("a", "p1"), cache_salt("b", "p1"))
        self.assertNotEqual(batch_key(item), batch_key(InferenceRequest("b", "b", "model", "p1", "a" * 64, 60, 40)))
        pool.release("one")
        self.assertTrue(pool.admit(second))
        with self.assertRaisesRegex(ContractError, "explicit network"):
            local_vllm_chat("http://127.0.0.1:8000", second, [{"role": "user", "content": "hi"}])
        with self.assertRaisesRegex(ContractError, "cache salt secret"):
            with patch.dict("os.environ", {"SWARMCONTEXT_CACHE_SALT_SECRET": "short"}):
                local_vllm_chat("http://127.0.0.1:8000", second,
                                [{"role": "user", "content": "hi"}], allow_network=True)

    def test_protocol_receipts_are_bounded_and_non_authorizing(self):
        envelope = task_envelope(task_id="t", agent_id="a", tenant_id="tenant",
                                 context_sha256="a" * 64, objective="Review the evidence")
        self.assertIn("not a conformant A2A", envelope["limits"])
        event = computer_use_event(provider="fixture", task_id="t", kind="observe",
                                   observation="private screenshot contents", side_effect=False)
        self.assertNotIn("private screenshot contents", str(event))
        chunks = cognee_chunks([{"id": "s1", "text": "a fact"}], tenant_id="tenant", query="fact")
        self.assertEqual(chunks[0]["text_untrusted"], "a fact")

    def test_demo_and_fleet_benchmark_limits(self):
        result = demo()
        self.assertEqual(result["task_state"], "completed")
        self.assertEqual(result["placement"], "container")
        report = benchmark_fleet(1000, 100, 10)
        self.assertEqual(report["logical_agents"], 1000)
        self.assertEqual(report["active_synthetic_tasks"], 100)
        self.assertIn("vLLM tokens/s", report["not_measured"])


if __name__ == "__main__":
    unittest.main()
