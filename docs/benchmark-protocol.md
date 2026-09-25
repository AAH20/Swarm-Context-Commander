# Benchmark protocol and release gates

For the cross-model, graph, human-interface and high-assurance evaluation contract, see the [evolution and evaluation standard](evolution-evaluation-standard.md) and its [metric matrix](../benchmarks/evolution-matrix.json). `swarm-context-commander eval-graph` is a four-record synthetic scope/revocation fixture, not a GraphRAG score.

## Claims must name a workload

`bench-fleet` tests local registration and in-memory scheduler operations. Run `--agents 150000 --active-tasks 10000 --tenants 100`, record host CPU, RAM, storage type, Python and SQLite versions, and publish raw JSON plus a revision SHA. The benchmark does not measure model, browser, A2A, Cognee or cluster behavior. Do not turn its `logical_agents` count into a concurrent-execution claim.

## Required comparison matrix

| Workload | Baselines | Required measurements |
| --- | --- | --- |
| Context memory | Recent-N, lexical only, full-context where feasible, Cognee, candidate `context-graph-compact` | Grounded answer/task success, source recall, contradictions, deletion propagation, tokens, p95 latency, cost |
| Browser work | Fixed scripted baseline and one OpenManus/Browser Use adapter | Accepted completion, side-effect errors, retry duplication, browser minutes, p95 duration |
| Scheduling | FIFO and weighted fair queue | Throughput, tail queue age, per-tenant starvation, cancellation, recovery, dollars per accepted task |
| Inference | Unmodified vLLM versus scoped prefix cache and admission | Input/output tokens/s, time to first token, p95 latency, KV occupancy, GPU cost, quality parity |
| A2A | Official SDK/conformance cases | Message/task/artifact compatibility, streaming, cancellation, authentication and restart behavior |
| Scale | 1k, 10k, 150k logical agents with separate 100, 1k and measured active-session loads | Registered descriptors, event/s, task/s, failures, storage, memory, capacity and cost |

Use the official [LongMemEval-V2](https://github.com/xiaowu0162/LongMemEval-V2/) and [LoCoMo](https://github.com/snap-research/locomo) harnesses for memory where permitted; use [BrowserGym](https://github.com/huggingface/OpenEnv/blob/main/docs/source/environments/browsergym.md) for reproducible computer-use tasks. Report dataset version, test split, answer model, judge, prompt, token budget, excluded cases and confidence intervals. Never compare leaderboard percentages across different protocols without rerunning a common harness.

## Production gates

1. Run cross-tenant, tombstone, idempotency, stale-lease and prompt-injection tests in CI.
2. Add a real A2A transport, native computer-use adapter, and isolated credential handling with integration tests.
3. Add Cognee-native graph ingestion and deletion tests, including stale replica and dataset-scope cases.
4. Replace SQLite and in-memory queue with durable partitioned services; validate crash recovery and load shedding.
5. Deploy an opt-in vLLM canary with model-specific throughput/latency/cost measurements and scoped prefix cache.
6. Validate Terraform/KEDA/GPU/VM templates in an isolated test cluster before documenting them as deployable.
7. Publish a 150k-logical-agent result alongside active-session and token-throughput figures, hardware bill and reproducibility package.
