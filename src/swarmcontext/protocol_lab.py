"""Deterministic protocol-composition lab over synthetic event traces.

The trace borrows concepts from A2A tasks, workload identity, Iceberg snapshots,
and telemetry receipts. It does not implement or certify any upstream protocol.
"""

from __future__ import annotations

import hashlib
from collections import Counter

from .registry import ContractError, canonical

SCHEMA = "swarmcontext-protocol-lab/v1"
EVENTS = {"identity_issued", "identity_revoked", "snapshot_committed", "authority_down",
          "authority_up", "task_submitted", "task_started", "task_finished", "telemetry_emitted"}


def _identifier(value: object, name: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 128 or any(ord(ch) < 33 for ch in value):
        raise ContractError(f"invalid {name}")
    return value


def _integer(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ContractError(f"invalid {name}")
    return value


def evaluate_trace(trace: dict) -> dict:
    """Replay a bounded trace; compare decisions with externally supplied labels."""
    if not isinstance(trace, dict) or trace.get("schema_version") != SCHEMA:
        raise ContractError("invalid protocol lab schema")
    name = _identifier(trace.get("scenario"), "scenario")
    max_age = _integer(trace.get("max_snapshot_age_s"), "max_snapshot_age_s")
    offline_read = _integer(trace.get("max_offline_read_s"), "max_offline_read_s")
    if max_age > 86400 or offline_read > 3600:
        raise ContractError("freshness or offline limit out of range")
    events = trace.get("events")
    if not isinstance(events, list) or not 1 <= len(events) <= 1000:
        raise ContractError("trace must contain 1-1000 events")
    if len(canonical(trace).encode()) > 256_000:
        raise ContractError("trace exceeds 256 KiB")

    identities: dict[str, dict] = {}
    snapshots: dict[str, dict] = {}
    tasks: dict[str, dict] = {}
    idempotency: dict[tuple[str, str], str] = {}
    side_effects: set[str] = set()
    decisions: list[dict] = []
    violations: list[dict] = []
    denial_reasons: Counter[str] = Counter()
    authority_up = True
    authority_down_at: int | None = None
    last_at = -1
    for position, event in enumerate(events):
        if not isinstance(event, dict) or event.get("kind") not in EVENTS:
            raise ContractError(f"invalid event at position {position}")
        kind = event["kind"]
        at = _integer(event.get("at_s"), "event time")
        if at < last_at:
            raise ContractError("events must be time ordered")
        last_at = at

        if kind == "identity_issued":
            key = _identifier(event.get("credential_id"), "credential_id")
            tenant = _identifier(event.get("tenant_id"), "tenant_id")
            expires = _integer(event.get("expires_at_s"), "expires_at_s")
            if key in identities or expires <= at:
                raise ContractError("credential duplicate or already expired")
            identities[key] = {"tenant": tenant, "expires": expires, "revoked": False}
        elif kind == "identity_revoked":
            key = _identifier(event.get("credential_id"), "credential_id")
            if key not in identities:
                raise ContractError("revocation refers to unknown credential")
            identities[key]["revoked"] = True
        elif kind == "snapshot_committed":
            key = _identifier(event.get("snapshot_id"), "snapshot_id")
            tenant = _identifier(event.get("tenant_id"), "tenant_id")
            if key in snapshots:
                raise ContractError("duplicate snapshot")
            snapshots[key] = {"tenant": tenant, "committed": at}
        elif kind == "authority_down":
            authority_up = False
            authority_down_at = at
        elif kind == "authority_up":
            authority_up = True
            authority_down_at = None
        elif kind == "task_submitted":
            key = _identifier(event.get("task_id"), "task_id")
            tenant = _identifier(event.get("tenant_id"), "tenant_id")
            idem = _identifier(event.get("idempotency_key"), "idempotency_key")
            credential = _identifier(event.get("credential_id"), "credential_id")
            snapshot = _identifier(event.get("snapshot_id"), "snapshot_id")
            operation = event.get("operation")
            if key in tasks or (tenant, idem) in idempotency or operation not in {"read", "write"}:
                raise ContractError("duplicate task/idempotency key or invalid operation")
            idempotency[(tenant, idem)] = key
            tasks[key] = {"tenant": tenant, "credential": credential, "snapshot": snapshot,
                          "operation": operation, "state": "queued", "telemetry": False}
        elif kind == "task_started":
            key = _identifier(event.get("task_id"), "task_id")
            if key not in tasks or tasks[key]["state"] != "queued":
                violations.append({"event": position, "task_id": key, "reason": "invalid_transition"})
                continue
            task = tasks[key]
            identity = identities.get(task["credential"])
            snapshot = snapshots.get(task["snapshot"])
            if identity is None or identity["tenant"] != task["tenant"]:
                reason = "identity_scope"
            elif identity["revoked"] or at >= identity["expires"]:
                reason = "identity_inactive"
            elif snapshot is None or snapshot["tenant"] != task["tenant"]:
                reason = "snapshot_scope"
            elif at - snapshot["committed"] > max_age:
                reason = "snapshot_stale"
            elif not authority_up and task["operation"] == "write":
                reason = "authority_unavailable_for_write"
            elif not authority_up and authority_down_at is not None and at - authority_down_at > offline_read:
                reason = "offline_read_window_expired"
            else:
                reason = "allowed"
            allowed = reason == "allowed"
            task["state"] = "running" if allowed else "denied"
            if not allowed:
                denial_reasons[reason] += 1
            expected = event.get("expected")
            if expected not in {"allow", "deny"}:
                raise ContractError("task start lacks frozen expected label")
            decisions.append({"task_id": key, "decision": "allow" if allowed else "deny",
                              "expected": expected, "reason": reason})
        elif kind == "task_finished":
            key = _identifier(event.get("task_id"), "task_id")
            task = tasks.get(key)
            if task is None or task["state"] != "running":
                violations.append({"event": position, "task_id": key, "reason": "invalid_transition"})
                continue
            status = event.get("status")
            if status not in {"completed", "failed", "cancelled"}:
                raise ContractError("invalid terminal status")
            task["state"] = status
            if task["operation"] == "write" and status == "completed":
                effect = _identifier(event.get("side_effect_id"), "side_effect_id")
                if effect in side_effects:
                    violations.append({"event": position, "task_id": key, "reason": "duplicate_side_effect"})
                side_effects.add(effect)
        else:  # telemetry_emitted
            key = _identifier(event.get("task_id"), "task_id")
            if key not in tasks or tasks[key]["state"] not in {"completed", "failed", "cancelled", "denied"}:
                violations.append({"event": position, "task_id": key, "reason": "orphan_or_early_telemetry"})
            else:
                tasks[key]["telemetry"] = True

    false_allows = sum(item["decision"] == "allow" and item["expected"] == "deny" for item in decisions)
    false_denials = sum(item["decision"] == "deny" and item["expected"] == "allow" for item in decisions)
    missing = sorted(key for key, task in tasks.items()
                     if task["state"] in {"completed", "failed", "cancelled", "denied"} and not task["telemetry"])
    input_hash = hashlib.sha256(canonical(trace).encode()).hexdigest()
    return {"schema_version": "swarmcontext-protocol-lab-result/v1", "scenario": name,
            "input_sha256": input_hash, "decision_count": len(decisions), "decisions": decisions,
            "false_allows": false_allows, "false_denials": false_denials,
            "denial_reasons": dict(sorted(denial_reasons.items())), "violations": violations,
            "missing_telemetry_task_ids": missing,
            "terminal_task_count": sum(task["state"] in {"completed", "failed", "cancelled", "denied"}
                                       for task in tasks.values()),
            "passing": false_allows == 0 and false_denials == 0 and not violations and not missing
                       and all(task["state"] != "queued" and task["state"] != "running" for task in tasks.values()),
            "claim": "synthetic_local_composition_only",
            "not_measured": ["native_a2a_conformance", "real_iam_or_pam", "native_iceberg",
                             "native_otlp", "distributed_recovery", "bgp", "pqc", "classified_authorization"]}
