import json
import unittest
from pathlib import Path

from swarmcontext.protocol_lab import evaluate_trace
from swarmcontext.registry import ContractError


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/protocol-lab.synthetic.json"


def sample():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class ProtocolLabTest(unittest.TestCase):
    def test_profile_matrix_separates_synthetic_and_proposed(self):
        profiles = json.loads((FIXTURE.parents[1] / "benchmarks/protocol-profiles.json").read_text())
        self.assertEqual(profiles["schema_version"], "swarmcontext-protocol-profiles/v1")
        ids = [profile["id"] for profile in profiles["profiles"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), {"a2a", "iam_pam", "data_bi", "bgp_rpki", "pqc", "high_assurance"})
        for profile in profiles["profiles"]:
            self.assertNotEqual(profile["status"], "native_verified")
            self.assertTrue(profile["metrics"])
            self.assertTrue(profile["hard_gate"])

    def test_fixture_has_expected_decisions_and_complete_telemetry(self):
        result = evaluate_trace(sample())
        self.assertTrue(result["passing"])
        self.assertEqual(result["decision_count"], 7)
        self.assertEqual(result["terminal_task_count"], 7)
        self.assertEqual(result["false_allows"], 0)
        self.assertEqual(result["false_denials"], 0)
        self.assertEqual(result["denial_reasons"]["authority_unavailable_for_write"], 1)
        self.assertEqual(result["denial_reasons"]["identity_inactive"], 1)
        self.assertEqual(result["denial_reasons"]["identity_scope"], 1)
        self.assertEqual(result["denial_reasons"]["snapshot_stale"], 1)

    def test_missing_telemetry_fails_gate(self):
        trace = sample()
        trace["events"] = [e for e in trace["events"]
                           if not (e["kind"] == "telemetry_emitted" and e["task_id"] == "read-ok")]
        result = evaluate_trace(trace)
        self.assertFalse(result["passing"])
        self.assertEqual(result["missing_telemetry_task_ids"], ["read-ok"])

    def test_frozen_label_disagreement_fails_gate(self):
        trace = sample()
        next(e for e in trace["events"] if e["kind"] == "task_started" and e["task_id"] == "revoked")["expected"] = "allow"
        result = evaluate_trace(trace)
        self.assertFalse(result["passing"])
        self.assertEqual(result["false_denials"], 1)

    def test_offline_read_has_bounded_window(self):
        trace = sample()
        trace["max_offline_read_s"] = 4
        result = evaluate_trace(trace)
        self.assertFalse(result["passing"])
        self.assertEqual(result["denial_reasons"]["offline_read_window_expired"], 1)
        self.assertEqual(result["false_denials"], 1)

    def test_duplicate_side_effect_fails_gate(self):
        trace = sample()
        trace["events"].extend([
            {"kind": "task_submitted", "at_s": 34, "task_id": "write-again", "tenant_id": "tenant-a",
             "idempotency_key": "eight", "credential_id": "cred-a2", "snapshot_id": "snapshot-a2", "operation": "write"},
            {"kind": "task_started", "at_s": 35, "task_id": "write-again", "expected": "allow"},
            {"kind": "task_finished", "at_s": 36, "task_id": "write-again", "status": "completed", "side_effect_id": "effect-seven"},
            {"kind": "telemetry_emitted", "at_s": 37, "task_id": "write-again"},
        ])
        result = evaluate_trace(trace)
        self.assertFalse(result["passing"])
        self.assertEqual(result["violations"][0]["reason"], "duplicate_side_effect")

    def test_rejects_unsorted_events_and_reused_idempotency(self):
        unsorted = sample()
        unsorted["events"][5]["at_s"] = 0
        with self.assertRaises(ContractError):
            evaluate_trace(unsorted)

        duplicate = sample()
        submitted = next(e for e in duplicate["events"] if e["kind"] == "task_submitted" and e["task_id"] == "write-during-outage")
        submitted["idempotency_key"] = "one"
        with self.assertRaises(ContractError):
            evaluate_trace(duplicate)


if __name__ == "__main__":
    unittest.main()
