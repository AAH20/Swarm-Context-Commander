"""Validate and render the 100-workload planning catalog. No provider access."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "catalog" / "workloads.psv"
OUTPUT = ROOT / "docs" / "100-workloads.md"
JSON_OUTPUT = ROOT / "catalog" / "workloads.json"
FIELDS = ("id", "domain", "workload", "inputs", "evaluation", "unit_economics", "phase", "gate")
PHASES = {"P0", "P1", "P2", "R"}


def records() -> list[dict[str, str]]:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    if tuple(lines[0].split("|")) != FIELDS:
        raise ValueError("catalog header mismatch")
    rows = []
    for line_number, line in enumerate(lines[1:], 2):
        cells = line.split("|")
        if len(cells) != len(FIELDS) or any(not cell.strip() for cell in cells):
            raise ValueError(f"invalid row {line_number}")
        row = dict(zip(FIELDS, cells))
        if row["phase"] not in PHASES:
            raise ValueError(f"invalid phase at row {line_number}")
        rows.append(row)
    if [r["id"] for r in rows] != [f"{i:03d}" for i in range(1, 101)]:
        raise ValueError("catalog IDs must be exactly 001 through 100")
    domains = Counter(r["domain"] for r in rows)
    if len(domains) != 10 or any(count != 10 for count in domains.values()):
        raise ValueError("catalog must contain ten domains of ten workloads")
    return rows


def render(rows: list[dict[str, str]]) -> str:
    intro = """# 100 candidate use cases and workloads

**Status:** planning catalog, not 100 shipped integrations. All examples require explicit data rights, source provenance, independent evaluation and a production release gate. The current Swarm-Context-Commander kernel provides local reference primitives for context, task admission and synthetic evaluation; it does not connect to the data vendors or operate physical fleets. IDs are stable identifiers for discussion and comparison, not a priority ranking.

**Source-rights boundary.** Bloomberg Terminal access does not by itself establish rights for enterprise aggregation or model training; use an appropriate [Bloomberg Data License or approved API](https://professional.bloomberg.com/products/data/data-license/) entitlement. Moody's identifies [Orbis products as formerly including Osiris](https://www.moodys.com/web/en/us/capabilities/company-reference-data/orbis/orbis-national-and-country-products.html). [Argos Atlas's commercial tier](https://www.argosatlas.com/en/pricing/) mentions API access and commercial use, subject to actual terms. These are *candidate data sources*, not current connectors. No proprietary records are included in this repository.

**Evaluation rule.** Every workload needs a frozen baseline, independently accepted outcome, p50/p95 latency, error and exclusion counts, cohort or environment slices, drift, provenance and a zero-tolerance access-boundary test. Synthetic success is a test of the harness, never proof of real demand or field safety. Financial, legal, employment and high-consequence decisions remain with qualified humans.

**Unit-economics rule.** For each row, the displayed denominator defines the unit. Fully loaded cost includes permitted data-license allocation, ingestion, model and GPU idle cost, CPU/browser/VM time, storage and egress, human review, rework, observability, security/compliance and support. `Cost per accepted unit = fully loaded cost / independently accepted units`; report zero-denominator cases as undefined, not zero. For comparative pilots, also report incremental benefit and cost against a locked incumbent with uncertainty intervals. Forecasted savings or avoided failures need validated counterfactuals.

**Phases.** `P0` means an inspectable synthetic or local baseline is a plausible next build; `P1` means consented read-only pilot after source rights and adapter tests; `P2` means sandbox/lab research before operational use; `R` means restricted, high-consequence assurance work with independent legal, safety and human-authority review. Every row is a *suggested workload*, not a claim of current deployment.

## Workload map

```mermaid
flowchart LR
  D[Licensed and public data] --> B[Continuous BI and entity graph]
  B --> S[Synthetic clean environments]
  B --> A[Audience, pricing and due diligence]
  S --> C[Computer-use and agent fleet evaluation]
  C --> P[Physical AI lab and digital twins]
  B --> G["GRC and defensive ATT&CK evaluation"]
  C --> G
  P --> G
  G --> H[Independent human release authority]
  H --> O[Measured accepted outcomes and unit economics]
  O --> B
```

"""
    sections = {
        "Licensed data": "Licensed and public data aggregation",
        "Continuous BI": "Data science and continuous business intelligence",
        "Synthetic data": "Synthetic clean environments and training datasets",
        "Audience lab": "Synthetic audiences, products, pricing and funnels",
        "Due diligence": "Customer, investor, vendor and transaction diligence",
        "Computer use": "Advanced computer-use agents",
        "Agent fleet": "Agent swarms, GraphRAG and inference infrastructure",
        "Physical AI": "Physical AI, VLA models and fleet commanders",
        "Cyber defense": "GRC, IAM/PAM and ATT&CK-informed defense",
        "Dual-use assurance": "Dual-use intelligence and military-adjacent assurance",
    }
    parts = [intro]
    for domain, title in sections.items():
        parts.append(f"## {title}\n\n")
        parts.append("| ID | Workload | Candidate inputs | Evaluation / KPI | Fully loaded unit-cost denominator | Phase | Hard gate |\n")
        parts.append("| --- | --- | --- | --- | --- | --- | --- |\n")
        for row in rows:
            if row["domain"] != domain:
                continue
            parts.append("| " + " | ".join(row[key] for key in ("id", "workload", "inputs", "evaluation", "unit_economics", "phase", "gate")) + " |\n")
        parts.append("\n")
    parts.append("""## ATT&CK and dual-use evidence contract

Workloads 081–090 and 098 use [MITRE ATT&CK Enterprise](https://attack.mitre.org/matrices/enterprise/) and, where industrial-control assurance is relevant, [ATT&CK ICS](https://attack.mitre.org/matrices/ics/) as **defensive classification and evaluation sources**. Import versioned [STIX data](https://attack.mitre.org/resources/working-with-attack/) rather than hard-coding a timeless list. Pin the ATT&CK release and map each scenario to `technique_id`, tactic, `detection_strategy_id`, analytic ID, tested control, permitted telemetry, evidence ID, reviewer label and observed outcome. MITRE's older [data-source list is deprecated](https://attack.mitre.org/datasources/); use its current detection strategies, analytics and data components when constructing fresh coverage claims. For AI-specific threat modeling, consider [MITRE ATLAS](https://atlas.mitre.org/); for defensive countermeasure vocabulary, [MITRE D3FEND](https://d3fend.mitre.org/).

Examples to validate on current MITRE pages: [T1078 Valid Accounts](https://attack.mitre.org/techniques/T1078/) for identity telemetry, [T1213 Data from Information Repositories](https://attack.mitre.org/techniques/T1213/) for repository audit review, and [T1021 Remote Services](https://attack.mitre.org/techniques/T1021/) for remote-session monitoring. The catalog uses these to evaluate detections and access boundaries; it contains no intrusion, targeting, covert collection or weapon-control procedure. A technique mapped on paper is not detection coverage. Coverage requires a reproducible test, measured precision and recall, false-negative analysis, detection latency and a named owner for gaps.

## Cross-project boundaries

- [Swarm-Context-Commander](../README.md) owns the inspectable context/admission kernel and benchmark contracts.
- [GRC Claw](https://github.com/AAH20/GRC_Claw), [Physical AI Governor](https://github.com/AAH20/physical-ai-governor), [Audience Swarm Lab](https://github.com/AAH20/audience-swarm-lab), [Outcome Fabric](https://github.com/AAH20/outcome-fabric) and other A2Z projects are **candidate** workload producers, reviewers or evidence consumers. A link here is not a tested integration.
- The [project reference ledger](project-references.md) distinguishes actual adapter code from architectural inspiration.

The strongest immediate P0 pilot is one authorized, read-only dataset plus one measurable task, such as filing-change review or website QA. The broader catalog becomes credible through independently accepted results and source rights, not by connecting all 100 sources at once.
""")
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated document is stale")
    args = parser.parse_args()
    rows = records()
    document = render(rows)
    payload = json.dumps({"schema_version": "swarmcontext-workloads/v1",
                          "claim": "planning_catalog_only",
                          "workloads": rows}, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != document:
            raise SystemExit("docs/100-workloads.md is stale; run python scripts/build_workload_catalog.py")
        if not JSON_OUTPUT.exists() or JSON_OUTPUT.read_text(encoding="utf-8") != payload:
            raise SystemExit("catalog/workloads.json is stale; run python scripts/build_workload_catalog.py")
        print("100-workload catalog is current")
    else:
        OUTPUT.write_text(document, encoding="utf-8")
        JSON_OUTPUT.write_text(payload, encoding="utf-8")
        print(OUTPUT)


if __name__ == "__main__":
    main()
