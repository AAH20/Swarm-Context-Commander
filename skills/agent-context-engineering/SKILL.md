---
name: agent-context-engineering
description: Design and measure bounded memory, context selection, and runtime admission for multi-agent systems using Swarm-Context-Commander. Use when an agent workflow needs source-linked context, tenant isolation review, token budgets, or reproducible fleet capacity claims.
---

# Agent context engineering

Use the local reference implementation when available. Start with `swarm-context-commander demo` and inspect the resulting bundle and worker receipt. For a request's own documents, use `swarm-context-mcp` with `compile_agent_context`; its records are inline and untrusted. Set a token budget and compare selected source digests against expected sources. Do not treat a supplied tenant ID as authentication.

For runtime planning, use `classify_agent_runtime` to compare serverless, container, and microVM placement. That tool classifies a task; it does not provision or run workers. For capacity claims, run `swarm-context-commander bench-fleet` and report the host, counts, measured timings, and excluded workload dimensions. Logical-agent registration is not active-model concurrency.

When adapting this design to another system, keep the retrieval baseline and policy fixed while comparing new GraphRAG, vector, or compression adapters. Measure recall, contamination, cost per accepted task, p95 latency, and task recovery independently. Follow [the benchmark protocol](../../docs/benchmark-protocol.md) for definitions. Obtain explicit authorization before using customer data or enabling network integrations.
