# Discoverability and listing claims

The primary search-intent pages are the README (AI agent memory, context engineering, multi-agent orchestration), [MCP installation](mcp-server.md) (MCP server for agent context), and [benchmark protocol](benchmark-protocol.md) (logical-agent capacity and cost). These phrases describe implemented capabilities or clearly marked comparisons. Google Trends provides relative interest, not absolute monthly search volume; no numeric search-volume or ranking claim is made here without a dated export from a named market.

Distribution surfaces and requirements:

| Surface | Artifact | Gate |
| --- | --- | --- |
| GitHub search | Description, topics, README, versioned releases | Repository published |
| skills.sh | `skills/agent-context-engineering/SKILL.md` | Remote `npx skills add AAH20/Swarm-Context-Commander --list` discovers it |
| Glama | Public repo, stdio server, Dockerfile, `glama.json` | Submit GitHub URL and pass their automated inspection |
| Hugging Face Spaces | `listings/huggingface-space/` | Owner must be logged in to create a public static Space |
| Official MCP Registry | Public package and `server.json` | PyPI or other supported package must be published and ownership verified first |
| Smithery | Hosted URL or MCPB bundle | Requires supported deployment and publisher authentication |

The Hugging Face page is an illustrative JavaScript demo. Its selection logic and metrics are not a substitute for the Python package tests. The official MCP Registry manifest will be added only with a real versioned public package, so directory metadata never promises an unavailable install.
