"""Bounded vLLM-compatible inference admission and local HTTP adapter."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from urllib import error, request
from urllib.parse import urlsplit

from .registry import ContractError, canonical


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ContractError("vLLM HTTP redirects are not allowed")


@dataclass(frozen=True)
class InferenceRequest:
    request_id: str
    tenant_id: str
    model: str
    policy_version: str
    context_sha256: str
    input_tokens: int
    max_output_tokens: int


def cache_salt(tenant_id: str, policy_version: str, *, secret: bytes | None = None) -> str:
    if not tenant_id or not policy_version:
        raise ContractError("tenant and context policy version required")
    value = canonical([tenant_id, policy_version]).encode()
    return (hmac.new(secret, value, hashlib.sha256).hexdigest() if secret is not None
            else hashlib.sha256(value).hexdigest())


class TokenAdmission:
    """Hard in-flight token reservations; caller releases on completion/failure."""

    def __init__(self, *, global_limit: int, tenant_limit: int):
        if global_limit < 1 or tenant_limit < 1 or tenant_limit > global_limit:
            raise ContractError("invalid token limits")
        self.global_limit = global_limit
        self.tenant_limit = tenant_limit
        self.active: dict[str, InferenceRequest] = {}
        self.by_tenant: dict[str, int] = defaultdict(int)
        self.reserved = 0

    def admit(self, item: InferenceRequest) -> bool:
        if (not item.request_id or not item.tenant_id or not item.model or not item.policy_version
                or len(item.context_sha256) != 64 or any(c not in "0123456789abcdef" for c in item.context_sha256)
                or item.input_tokens < 1 or item.max_output_tokens < 1 or item.request_id in self.active):
            raise ContractError("invalid or duplicate inference request")
        cost = item.input_tokens + item.max_output_tokens
        if self.reserved + cost > self.global_limit or self.by_tenant[item.tenant_id] + cost > self.tenant_limit:
            return False
        self.active[item.request_id] = item
        self.reserved += cost
        self.by_tenant[item.tenant_id] += cost
        return True

    def release(self, request_id: str) -> None:
        try:
            item = self.active.pop(request_id)
        except KeyError as exc:
            raise ContractError("unknown inference reservation") from exc
        cost = item.input_tokens + item.max_output_tokens
        self.reserved -= cost
        self.by_tenant[item.tenant_id] -= cost


def batch_key(item: InferenceRequest) -> tuple[str, str, str]:
    """Group candidates only; the actual vLLM engine controls continuous batching."""
    return item.model, item.policy_version, cache_salt(item.tenant_id, item.policy_version)


def local_vllm_chat(base_url: str, item: InferenceRequest, messages: list[dict], *, allow_network: bool = False) -> dict:
    """Optional loopback call; never runs during a default test or benchmark."""
    parsed = urlsplit(base_url)
    if (parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1")
            or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
        raise ContractError("vLLM URL must be a local HTTP origin")
    if not allow_network:
        raise ContractError("explicit network opt-in required")
    secret = os.environ.get("SWARMCONTEXT_CACHE_SALT_SECRET", "")
    if len(secret) < 32:
        raise ContractError("local vLLM call requires a 32+ character cache salt secret")
    if not isinstance(messages, list) or len(messages) > 16 or any(
            not isinstance(m, dict) or set(m) != {"role", "content"}
            or m["role"] not in ("system", "user", "assistant")
            or not isinstance(m["content"], str) for m in messages):
        raise ContractError("invalid bounded chat messages")
    payload = {"model": item.model, "messages": messages, "max_tokens": item.max_output_tokens,
               "cache_salt": cache_salt(item.tenant_id, item.policy_version, secret=secret.encode())}
    body = canonical(payload).encode()
    if len(body) > 65536:
        raise ContractError("vLLM request exceeds 64 KiB")
    req = request.Request(base_url.rstrip("/") + "/v1/chat/completions", body,
                          headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.build_opener(_NoRedirect()).open(req, timeout=30) as response:
            raw = response.read(65537)
    except (error.URLError, TimeoutError) as exc:
        raise ContractError(f"local vLLM request failed: {type(exc).__name__}") from exc
    if len(raw) > 65536:
        raise ContractError("vLLM response exceeds 64 KiB")
    try:
        result = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("vLLM response is not JSON") from exc
    if not isinstance(result, dict) or not isinstance(result.get("choices"), list):
        raise ContractError("vLLM response lacks choices")
    return result
