# MCP server: AI agent memory and runtime placement

Install Python 3.10+ and the optional official MCP Python SDK:

```bash
python3 -m pip install '.[mcp]'
swarm-context-mcp
```

Configure an MCP host to launch `swarm-context-mcp` over stdio. The server offers two tools:

| Tool | Input | Output |
| --- | --- | --- |
| `compile_agent_context` | Query, up to 64 inline records, token budget and item cap | Source-linked lexical context bundle |
| `classify_agent_runtime` | Token estimate and browser/code/isolation flags | Serverless, container or microVM recommendation |

Example host entry:

```json
{
  "mcpServers": {
    "swarm-context-commander": {
      "command": "swarm-context-mcp"
    }
  }
}
```

The server does not authenticate users, read files, call models, execute code or retain records. Inline documents are treated as untrusted data. Do not expose the stdio process as a multi-tenant remote service without an authenticated gateway and access checks. Token counts are estimates, not model-tokenizer counts. This is the installable MCP boundary for the local reference; a hosted service remains future work.
