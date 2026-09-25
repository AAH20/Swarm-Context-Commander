import collections
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkloadCatalogTests(unittest.TestCase):
    def test_exactly_100_proposals_in_ten_balanced_domains(self):
        payload = json.loads((ROOT / "catalog/workloads.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["claim"], "planning_catalog_only")
        rows = payload["workloads"]
        self.assertEqual([row["id"] for row in rows], [f"{number:03d}" for number in range(1, 101)])
        self.assertEqual(sorted(collections.Counter(row["domain"] for row in rows).values()), [10] * 10)
        self.assertTrue(all(row["phase"] in {"P0", "P1", "P2", "R"} for row in rows))
        self.assertTrue(all(row["evaluation"] and row["unit_economics"] and row["gate"] for row in rows))

    def test_rendered_document_and_json_are_current(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/build_workload_catalog.py"), "--check"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
