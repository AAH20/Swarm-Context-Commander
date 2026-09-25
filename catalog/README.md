# Workload catalog source

`workloads.psv` is the reviewed source of truth for 100 **proposed** workloads. Each row has a stable ID, domain, candidate workload, candidate inputs, evaluation metrics, fully loaded unit-cost denominator, phase and hard release gate. Edit the PSV and run:

```bash
python3 scripts/build_workload_catalog.py
python3 scripts/build_workload_catalog.py --check
```

The generator validates exactly IDs `001`–`100` in ten domains of ten entries, then produces `workloads.json` and [`docs/100-workloads.md`](../docs/100-workloads.md). JSON includes the `planning_catalog_only` claim. None of these rows grants data access, creates a vendor connector, or represents a deployed use case. The listed sources require their own contracts, licenses, privacy review and independent acceptance criteria.
