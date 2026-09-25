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

As of September 25, 2026, the [skills.sh page](https://skills.sh/aah20/swarm-context-commander/agent-context-engineering) is live and [awesome-mcp-servers PR #15068](https://github.com/punkpeye/awesome-mcp-servers/pull/15068) is open. That list requires a Glama listing and badge before merge. Glama currently asks for signup before server submission. PulseMCP has paused new submissions; MCP.so currently presents a paid submission path. None of those pending surfaces is described as a published listing.
