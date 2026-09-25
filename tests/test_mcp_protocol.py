"""Real SDK stdio handshake and tool call; requires the optional MCP extra."""

import asyncio
import sys
import unittest


class MCPProtocolTest(unittest.TestCase):
    def test_stdio_handshake_and_tool_call(self):
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            self.skipTest("install the optional mcp extra")

        async def check():
            params = StdioServerParameters(command=sys.executable,
                                            args=["-m", "swarmcontext.mcp_server"])
            async with stdio_client(params) as (reader, writer):
                async with ClientSession(reader, writer) as client:
                    await client.initialize()
                    names = {tool.name for tool in (await client.list_tools()).tools}
                    self.assertEqual(names, {"compile_agent_context", "classify_agent_runtime"})
                    result = await client.call_tool("classify_agent_runtime",
                                                    {"estimated_tokens": 100, "needs_browser": True})
                    self.assertFalse(result.isError)
                    self.assertIn("container", result.content[0].text)

        asyncio.run(check())
