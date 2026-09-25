"""Local, stateless MCP tools for bounded context and placement decisions.

No caller-provided tenant ID is treated as authentication. This server accepts
only records supplied in the current request and never reads private files.
"""

from __future__ import annotations

import hashlib
import time

from .context import ContextIndex, ContextPolicy, Memory
from .registry import ContractError
from .scheduler import Work, placement


def compile_context(query: str, records: list[dict], *, token_budget: int = 512,
                    max_items: int = 8) -> dict:
    """Compile a bounded context bundle from at most 64 caller-supplied records."""
    if not isinstance(query, str) or not 1 <= len(query) <= 240:
        raise ContractError("query must be 1-240 characters")
    if not isinstance(records, list) or len(records) > 64:
        raise ContractError("records must be a list of at most 64 items")
    policy = ContextPolicy(token_budget=token_budget, max_items=max_items)
    policy.validate()
    index = ContextIndex()
    for position, record in enumerate(records):
        if not isinstance(record, dict) or set(record) - {"text", "source_id"}:
            raise ContractError("record must contain only text and optional source_id")
        value = record.get("text")
        source = record.get("source_id", f"record-{position}")
        if not isinstance(value, str) or not 1 <= len(value) <= 4000:
            raise ContractError("record text must be 1-4000 characters")
        if not isinstance(source, str) or not 1 <= len(source) <= 128:
            raise ContractError("source_id must be 1-128 characters")
        index.add(Memory(f"input-{position}", "local-request", "tenant", value,
                         hashlib.sha256((source + "\0" + value).encode()).hexdigest(),
                         position, trust=0))
    result = index.compile(query, tenant="local-request", agent="local-agent",
                           now=int(time.time()), policy=policy)
    result["input_record_count"] = len(records)
    result["claim"] = "lexical_reference; records_are_untrusted; no_persistent_memory"
    return result


def recommend_placement(*, estimated_tokens: int, needs_browser: bool = False,
                        runs_code: bool = False, high_isolation: bool = False,
                        read_only: bool = True, estimated_seconds: int = 1) -> dict:
    """Classify a task for a runtime without executing or provisioning it."""
    if type(estimated_tokens) is not int or not 1 <= estimated_tokens <= 16384:
        raise ContractError("estimated_tokens must be 1-16384")
    if type(estimated_seconds) is not int or not 1 <= estimated_seconds <= 3600:
        raise ContractError("estimated_seconds must be 1-3600")
    if any(type(flag) is not bool for flag in (needs_browser, runs_code, high_isolation, read_only)):
        raise ContractError("runtime flags must be booleans")
    work = Work("local-task", "local-request", estimated_tokens,
                needs_browser=needs_browser, runs_code=runs_code,
                high_isolation=high_isolation, read_only=read_only,
                estimated_seconds=estimated_seconds)
    return {"placement": placement(work), "estimated_tokens": estimated_tokens,
            "claim": "classification_only; no_worker_launched"}


def create_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install the optional MCP dependency: pip install 'swarm-context-commander[mcp]'") from exc

    server = FastMCP("Swarm Context Commander")

    @server.tool()
    def compile_agent_context(query: str, records: list[dict], token_budget: int = 512,
                              max_items: int = 8) -> dict:
        """Select source-linked, untrusted text within a token budget from inline records."""
        return compile_context(query, records, token_budget=token_budget, max_items=max_items)

    @server.tool()
    def classify_agent_runtime(estimated_tokens: int, needs_browser: bool = False,
                               runs_code: bool = False, high_isolation: bool = False,
                               read_only: bool = True, estimated_seconds: int = 1) -> dict:
        """Recommend serverless, container, or microVM placement; does not execute."""
        return recommend_placement(estimated_tokens=estimated_tokens, needs_browser=needs_browser,
                                   runs_code=runs_code, high_isolation=high_isolation,
                                   read_only=read_only, estimated_seconds=estimated_seconds)

    return server


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
