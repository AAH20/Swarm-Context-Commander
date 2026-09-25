# Project references and integration status

Swarm-Context-Commander is an independent implementation. The original [Context Atlas](../listings/huggingface-space/index.html) and [SVG preview](../assets/context-atlas-preview.svg) use only synthetic fixtures and this repository's code. The links below identify **architectural references and potential interoperability boundaries**, not copied visual assets, endorsements, partnerships or claims of complete compatibility.

| Project | Idea or boundary relevant here | Present repository status |
| --- | --- | --- |
| [Cognee](https://github.com/topoteretes/cognee) | Graph-backed agent memory and retrieval candidates | A bounded, opt-in loopback `CHUNKS` adapter exists. The fixture/HTTP contract is tested with a mock; a live Cognee server, graph extraction and native deletion semantics are unverified. |
| [LangGraph](https://github.com/langchain-ai/langgraph) | Explicit graph/state transitions and durable agent workflow concepts | Conceptual reference. No LangGraph runtime, checkpoint store or API adapter is shipped. |
| [Deep Agents](https://github.com/langchain-ai/deepagents) | Long-running agent context, subagents and file-backed memory patterns | Conceptual reference. No Deep Agents integration or compatibility claim. |
| [A2A Protocol](https://github.com/a2aproject/A2A) | Task/message/artifact boundaries between agents | An A2A-inspired sidecar exists. It is not a conformant A2A server or client. |
| [Model Context Protocol](https://github.com/modelcontextprotocol/modelcontextprotocol) | Tool discovery and invocation surface | A local stdio MCP server exposes context compilation and placement tools; it is not a hosted multi-tenant service. |
| [vLLM](https://github.com/vllm-project/vllm) | Serving economics, continuous batching and scoped prefix-cache concepts | In-flight token admission and an opt-in, loopback vLLM-compatible chat client exist. No GPU fleet, native scheduler integration or throughput claim. |
| [Google AX](https://github.com/google/ax) | Task/workspace/isolation lifecycle for agent execution | Placement classification is inspired by this operating model. No AX deployment or executor adapter is present. |
| [OpenManus](https://github.com/FoundationAgents/OpenManus) | General computer-use agent workflow | Only a synthetic worker and normalized receipt contract exist. No OpenManus process or browser is launched. |
| [context-graph-compact](https://github.com/AAH20/context-graph-compact) | Candidate context compaction comparison | Future comparative evaluation target. It is not a dependency of the reference compiler. |

The Atlas's `DERIVED_FROM`, `SUPPLIES`, `INFORMS`, `CONSTRAINS`, `EVALUATES`, `AUTHORIZES`, `MEASURED_BY` and `BLOCKED` edges are **our illustrative relation vocabulary**. Edge confidence values are fixture values, not calibrated model probabilities. The current Python `ContextIndex` supports only hand-linked, one-hop graph expansion; it does not infer these typed edges. A future adapter must preserve edge provenance, temporal validity, trust, deletion lineage and access scope before its output can influence a task.

A real interoperability claim requires upstream-version pinning, contract tests, failure/retry tests, authorization checks and published benchmark results on representative workloads. [Architecture](architecture.md) and [personalization evaluation](personalization-and-learning.md) define the remaining gates.
