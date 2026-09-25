import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EvolutionMatrixTest(unittest.TestCase):
    def test_matrix_contract(self):
        matrix = json.loads((ROOT / "benchmarks/evolution-matrix.json").read_text())
        self.assertEqual(matrix["schema_version"], "swarmcontext-evolution-matrix/v1")
        phases = [entry["id"] for entry in matrix["phases"]]
        self.assertEqual(len(phases), len(set(phases)))
        metrics = matrix["metrics"]
        ids = [entry["id"] for entry in metrics]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(metrics), 20)
        for entry in metrics:
            self.assertIn(entry["phase"], phases)
            self.assertIn(entry["status"], {"local_fixture", "proposed"})
            self.assertIn(entry["direction"], {"maximize", "minimize", "target_interval", "report"})
            self.assertTrue(entry["formula"])
        self.assertTrue(matrix["policy"]["hard_gates_override_composite_score"])


if __name__ == "__main__":
    unittest.main()
