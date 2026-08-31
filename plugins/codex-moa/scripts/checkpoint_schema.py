"""Validation contracts for immutable Codex MoA checkpoints."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA_VERSION = 2
COUNCILS = {"luna-grok": ("gpt-5.6-luna", "grok-4.6"),
            "grok-gemini": ("grok-4.6", "gemini-3.7-flash-high")}
PHASES = {
    "preflight",
    "localize",
    "plan",
    "implement",
    "validate",
    "recover",
    "review",
    "complete",
    "blocked",
}
STATUSES = {"active", "complete", "blocked"}
VALIDATION_STATUSES = {"pending", "pass", "fail", "skipped"}
LEADER_MODES = set(COUNCILS)
LEGACY_LEADER_MODES = {"grok-led", "gemini-led"}
HANDLE_RE = re.compile(r"^[a-f0-9]{32}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SENSITIVE_KEY_RE = re.compile(
    r"(?:^|[_-])(api[_-]?key|token|secret|credential|password|authorization|cookie|account)(?:$|[_-])",
    re.IGNORECASE,
)
SECRET_VALUE_RES = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
)


class CheckpointError(ValueError):
    """A fail-closed checkpoint validation error."""


def _text(value: Any, field: str, *, maximum: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise CheckpointError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized and not allow_empty:
        raise CheckpointError(f"{field} must not be empty")
    if len(normalized) > maximum:
        raise CheckpointError(f"{field} exceeds {maximum} characters")
    for pattern in SECRET_VALUE_RES:
        if pattern.search(normalized):
            raise CheckpointError(f"{field} appears to contain a secret value")
    return normalized


def _string_list(value: Any, field: str, *, maximum_items: int, item_maximum: int) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise CheckpointError(f"{field} must be a list")
    if len(value) > maximum_items:
        raise CheckpointError(f"{field} exceeds {maximum_items} items")
    return [
        _text(item, f"{field}[{index}]", maximum=item_maximum)
        for index, item in enumerate(value)
    ]


def _mapping_list(
    value: Any,
    field: str,
    *,
    maximum_items: int,
    allowed_keys: set[str],
    required_keys: set[str],
) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise CheckpointError(f"{field} must be a list")
    if len(value) > maximum_items:
        raise CheckpointError(f"{field} exceeds {maximum_items} items")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise CheckpointError(f"{field}[{index}] must be an object")
        unknown = set(item) - allowed_keys
        missing = required_keys - set(item)
        if unknown:
            raise CheckpointError(f"{field}[{index}] has unsupported fields: {', '.join(sorted(unknown))}")
        if missing:
            raise CheckpointError(f"{field}[{index}] is missing: {', '.join(sorted(missing))}")
        clean: dict[str, Any] = {}
        for key, raw in item.items():
            if SENSITIVE_KEY_RE.search(str(key)):
                raise CheckpointError(f"{field}[{index}] contains a forbidden sensitive field")
            if key == "exit_code":
                if raw is not None and (not isinstance(raw, int) or isinstance(raw, bool)):
                    raise CheckpointError(f"{field}[{index}].exit_code must be an integer or null")
                clean[key] = raw
            elif key == "status":
                status = _text(raw, f"{field}[{index}].status", maximum=16)
                if status not in VALIDATION_STATUSES:
                    raise CheckpointError(f"{field}[{index}].status is unsupported")
                clean[key] = status
            else:
                maximum = 2048 if key in {"summary", "command", "transcript_ref"} else 256 if key == "reviewed_revision" else 128
                clean[key] = _text(raw, f"{field}[{index}].{key}", maximum=maximum)
        result.append(clean)
    return result


def _native_agents(raw: Any, advisor: str) -> list[dict[str, Any]]:
    agents = _mapping_list(raw, "native_agents", maximum_items=4,
        allowed_keys={"role", "model", "agent_id", "verdict", "summary", "transcript_ref", "reviewed_revision"},
        required_keys={"role", "model", "agent_id", "verdict", "summary", "transcript_ref"})
    seen: set[tuple[str, str]] = set()
    for agent in agents:
        if agent["role"] not in {"localizer", "critic", "reviewer", "recovery"}:
            raise CheckpointError("native_agents role is unsupported")
        if agent["model"] != advisor:
            raise CheckpointError("native agent model must equal the exact council advisor")
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{15,127}", agent["agent_id"]) is None:
            raise CheckpointError("native agent_id must be the actual opaque runtime agent identifier")
        pair = (agent["role"], agent["agent_id"])
        if pair in seen:
            raise CheckpointError("duplicate native agent witness")
        seen.add(pair)
        if agent["verdict"] not in {"OBSERVED", "APPROVE", "REQUEST_CHANGES"}:
            raise CheckpointError("native agent verdict is unsupported")
        if agent["role"] == "reviewer" and not agent.get("reviewed_revision"):
            raise CheckpointError("reviewer witness requires reviewed_revision for the actual final diff")
    return agents


def validate_checkpoint(raw: Any, *, allow_legacy: bool = False) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CheckpointError("checkpoint must be an object")
    version = raw.get("schema_version", SCHEMA_VERSION)
    legacy = version == 1 and allow_legacy
    if type(version) is not int or (version != SCHEMA_VERSION and not legacy):
        raise CheckpointError("new checkpoints require schema_version=2; historical schema 1 is read-only")
    allowed = {
        "schema_version",
        "run_id",
        "objective",
        "phase",
        "status",
        "leader_mode",
        "leader_model",
        "advisor_models",
        "constraints",
        "decisions",
        "evidence",
        "owned_paths",
        "changed_paths",
        "validation",
        "risks",
        "next_action",
        "retry_budget",
        "previous",
    }
    unknown = set(raw) - allowed
    if not legacy:
        unknown -= {"council", "native_agents"}
    if unknown:
        raise CheckpointError(f"checkpoint has unsupported fields: {', '.join(sorted(unknown))}")
    for key in raw:
        if SENSITIVE_KEY_RE.search(str(key)):
            raise CheckpointError(f"checkpoint contains forbidden sensitive field {key!r}")

    run_id = _text(raw.get("run_id"), "run_id", maximum=128)
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise CheckpointError("run_id must use letters, digits, dot, underscore, or hyphen")
    phase = _text(raw.get("phase"), "phase", maximum=16)
    if phase not in PHASES:
        raise CheckpointError(f"unsupported phase {phase!r}")
    status = _text(raw.get("status", "active"), "status", maximum=16)
    if status not in STATUSES:
        raise CheckpointError(f"unsupported status {status!r}")
    leader_mode = _text(raw.get("leader_mode"), "leader_mode", maximum=16)
    if leader_mode not in (LEGACY_LEADER_MODES if legacy else LEADER_MODES):
        raise CheckpointError(f"unsupported leader_mode {leader_mode!r}")
    leader_model = _text(raw.get("leader_model"), "leader_model", maximum=256)
    advisor_models = _string_list(raw.get("advisor_models"), "advisor_models", maximum_items=4, item_maximum=256)
    if leader_model in advisor_models:
        raise CheckpointError("leader_model must not be duplicated in advisor_models")

    previous = raw.get("previous")
    if not legacy:
        council = _text(raw.get("council"), "council", maximum=32)
        if council not in COUNCILS or leader_mode != council:
            raise CheckpointError("council and leader_mode must name the same supported council")
        expected_leader, expected_advisor = COUNCILS[council]
        if leader_model != expected_leader or advisor_models != [expected_advisor]:
            raise CheckpointError("leader/advisor models must exactly match the named council")
        native_agents = _native_agents(raw.get("native_agents"), expected_advisor)
    if previous is not None:
        previous = _text(previous, "previous", maximum=32)
        if HANDLE_RE.fullmatch(previous) is None:
            raise CheckpointError("previous must be an opaque checkpoint handle")
    retry_budget = raw.get("retry_budget", 2)
    if not isinstance(retry_budget, int) or isinstance(retry_budget, bool) or not 0 <= retry_budget <= 2:
        raise CheckpointError("retry_budget must be an integer from 0 through 2")

    clean = {
        "schema_version": version,
        "run_id": run_id,
        "objective": _text(raw.get("objective"), "objective", maximum=8000),
        "phase": phase,
        "status": status,
        "leader_mode": leader_mode,
        "leader_model": leader_model,
        "advisor_models": advisor_models,
        "constraints": _string_list(raw.get("constraints"), "constraints", maximum_items=64, item_maximum=1024),
        "decisions": _string_list(raw.get("decisions"), "decisions", maximum_items=64, item_maximum=2048),
        "evidence": _mapping_list(
            raw.get("evidence"),
            "evidence",
            maximum_items=96,
            allowed_keys={"kind", "summary", "command", "exit_code"},
            required_keys={"kind", "summary"},
        ),
        "owned_paths": _string_list(raw.get("owned_paths"), "owned_paths", maximum_items=256, item_maximum=512),
        "changed_paths": _string_list(raw.get("changed_paths"), "changed_paths", maximum_items=256, item_maximum=512),
        "validation": _mapping_list(
            raw.get("validation"),
            "validation",
            maximum_items=96,
            allowed_keys={"command", "status", "summary", "exit_code"},
            required_keys={"command", "status", "summary"},
        ),
        "risks": _string_list(raw.get("risks"), "risks", maximum_items=64, item_maximum=2048),
        "next_action": _text(raw.get("next_action"), "next_action", maximum=4000),
        "retry_budget": retry_budget,
        "previous": previous,
    }
    if not legacy:
        clean.update(council=council, native_agents=native_agents)
        if phase == "complete":
            if status != "complete" or previous is None:
                raise CheckpointError("complete phase requires complete status and previous review checkpoint")
            reviewers = [agent for agent in native_agents if agent["role"] == "reviewer"]
            if not reviewers or any(agent["verdict"] != "APPROVE" for agent in reviewers):
                raise CheckpointError("completion requires a returned native reviewer APPROVE witness")
            if not clean["validation"] or any(item["status"] != "pass" or item.get("exit_code") != 0 for item in clean["validation"]):
                raise CheckpointError("completion requires successful repository validation with exit_code=0")
    if clean["status"] == "complete" and clean["phase"] != "complete":
        raise CheckpointError("complete status requires phase=complete")
    if clean["status"] == "blocked" and clean["phase"] != "blocked":
        raise CheckpointError("blocked status requires phase=blocked")
    return clean


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def checkpoint_digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()
