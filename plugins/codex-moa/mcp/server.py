#!/usr/bin/env python3
"""Native Codex MoA checkpoint MCP server.

The server is deliberately narrow: it stores immutable, validated progress
records. It does not call models, execute commands, route accounts, or run an
agent loop.
"""
from __future__ import annotations

import argparse
import datetime as dt
import errno
import json
import os
import re
import stat
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, BinaryIO, Mapping

SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from checkpoint_schema import (  # noqa: E402
    HANDLE_RE,
    CheckpointError,
    checkpoint_digest,
    validate_checkpoint,
)

SERVER_NAME = "codex-moa-checkpoints"
SERVER_VERSION = "2.0.0"
PROTOCOL_VERSION = "2025-06-18"
MAX_MESSAGE_BYTES = 2 * 1024 * 1024
MAX_CHECKPOINTS = 2_000


class StoreError(RuntimeError):
    """Checkpoint storage or authority error."""


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _reject_symlink(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    if stat.S_ISLNK(mode):
        raise StoreError(f"{label} must not be a symlink: {path}")


def _reject_symlink_chain(path: Path, label: str) -> None:
    current = path
    existing: list[Path] = []
    while True:
        existing.append(current)
        if current.parent == current:
            break
        current = current.parent
    for candidate in reversed(existing):
        _reject_symlink(candidate, label)


class CheckpointStore:
    def __init__(self, root: Path | None = None) -> None:
        codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
        selected = root.expanduser() if root is not None else codex_home / "codex-moa" / "checkpoints"
        if not selected.is_absolute():
            raise StoreError("checkpoint directory must be an absolute path")
        self.root = selected

    def ensure_root(self) -> None:
        _reject_symlink_chain(self.root, "checkpoint path")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        _reject_symlink_chain(self.root, "checkpoint path")
        os.chmod(self.root, 0o700)
        if _mode(self.root) != 0o700:
            raise StoreError("checkpoint directory mode must be 0700")

    def _path(self, handle: str) -> Path:
        if HANDLE_RE.fullmatch(handle) is None:
            raise StoreError("invalid opaque checkpoint handle")
        return self.root / f"{handle}.json"

    def _load_path(self, path: Path) -> dict[str, Any]:
        _reject_symlink(path, "checkpoint file")
        try:
            raw = path.read_text(encoding="utf-8")
            value = json.loads(raw)
        except FileNotFoundError as exc:
            raise StoreError("checkpoint not found") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise StoreError(f"cannot read checkpoint: {exc}") from exc
        if not isinstance(value, dict):
            raise StoreError("checkpoint record has an invalid shape")
        handle = path.stem
        if value.get("handle") != handle:
            raise StoreError("checkpoint record handle mismatch")
        checkpoint = value.get("checkpoint")
        try:
            clean = validate_checkpoint(checkpoint)
        except CheckpointError as exc:
            raise StoreError(f"stored checkpoint failed validation: {exc}") from exc
        digest = checkpoint_digest(clean)
        if value.get("digest") != digest:
            raise StoreError("stored checkpoint digest mismatch")
        value["checkpoint"] = clean
        return value

    def get(self, handle: str) -> dict[str, Any]:
        self.ensure_root()
        return self._load_path(self._path(handle))

    def _records(self) -> list[dict[str, Any]]:
        self.ensure_root()
        paths = sorted(self.root.glob("*.json"))
        if len(paths) > MAX_CHECKPOINTS:
            raise StoreError(f"checkpoint store exceeds the {MAX_CHECKPOINTS} record safety limit")
        records: list[dict[str, Any]] = []
        for path in paths:
            if HANDLE_RE.fullmatch(path.stem) is None:
                continue
            records.append(self._load_path(path))
        records.sort(key=lambda item: (str(item.get("created_at", "")), str(item.get("handle", ""))))
        return records

    def put(self, raw: Any) -> tuple[dict[str, Any], bool]:
        self.ensure_root()
        try:
            checkpoint = validate_checkpoint(raw)
        except CheckpointError as exc:
            raise StoreError(str(exc)) from exc

        previous = checkpoint.get("previous")
        if previous:
            previous_record = self.get(previous)
            if previous_record["checkpoint"]["run_id"] != checkpoint["run_id"]:
                raise StoreError("previous checkpoint belongs to a different run_id")

        digest = checkpoint_digest(checkpoint)
        records = self._records()
        for record in reversed(records):
            if (
                record["checkpoint"]["run_id"] == checkpoint["run_id"]
                and record["digest"] == digest
            ):
                return record, False

        if len(records) >= MAX_CHECKPOINTS:
            raise StoreError(f"checkpoint store reached the {MAX_CHECKPOINTS} record safety limit")

        handle = uuid.uuid4().hex
        record = {
            "handle": handle,
            "created_at": _utc_now(),
            "digest": digest,
            "checkpoint": checkpoint,
        }
        target = self._path(handle)
        payload = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        fd, temp_name = tempfile.mkstemp(prefix=".checkpoint-", suffix=".tmp", dir=self.root)
        temp_path = Path(temp_name)
        try:
            os.chmod(temp_path, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            if target.exists():
                raise StoreError("opaque checkpoint handle collision")
            try:
                os.link(temp_path, target, follow_symlinks=False)
            except FileExistsError as exc:
                raise StoreError("opaque checkpoint handle collision") from exc
            temp_path.unlink()
            os.chmod(target, 0o600)
            if _mode(target) != 0o600:
                raise StoreError("checkpoint file mode must be 0600")
            try:
                directory_fd = os.open(self.root, os.O_RDONLY)
            except OSError:
                directory_fd = None
            if directory_fd is not None:
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except Exception:
            temp_path.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
            raise
        return record, True

    def list(self, *, run_id: str | None, limit: int) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise StoreError("limit must be an integer from 1 through 100")
        if run_id is not None:
            if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id.strip()):
                raise StoreError("run_id filter is invalid")
            run_id = run_id.strip()
        records = self._records()
        if run_id is not None:
            records = [record for record in records if record["checkpoint"]["run_id"] == run_id]
        summaries: list[dict[str, Any]] = []
        for record in reversed(records[-limit:]):
            checkpoint = record["checkpoint"]
            summaries.append(
                {
                    "handle": record["handle"],
                    "created_at": record["created_at"],
                    "digest": record["digest"],
                    "run_id": checkpoint["run_id"],
                    "phase": checkpoint["phase"],
                    "status": checkpoint["status"],
                    "leader_mode": checkpoint["leader_mode"],
                    "next_action": checkpoint["next_action"],
                }
            )
        return summaries


def tool_definitions() -> list[dict[str, Any]]:
    checkpoint_schema: dict[str, Any] = {
        "type": "object",
        "required": [
            "run_id",
            "objective",
            "phase",
            "leader_mode",
            "leader_model",
            "next_action",
        ],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "run_id": {"type": "string", "minLength": 1, "maxLength": 128},
            "objective": {"type": "string", "minLength": 1, "maxLength": 8000},
            "phase": {
                "type": "string",
                "enum": [
                    "preflight",
                    "localize",
                    "plan",
                    "implement",
                    "validate",
                    "recover",
                    "review",
                    "complete",
                    "blocked",
                ],
            },
            "status": {"type": "string", "enum": ["active", "complete", "blocked"]},
            "leader_mode": {"type": "string", "enum": ["grok-led", "gemini-led"]},
            "leader_model": {"type": "string", "minLength": 1, "maxLength": 256},
            "advisor_models": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
            "constraints": {"type": "array", "maxItems": 64, "items": {"type": "string"}},
            "decisions": {"type": "array", "maxItems": 64, "items": {"type": "string"}},
            "evidence": {"type": "array", "maxItems": 96, "items": {"type": "object"}},
            "owned_paths": {"type": "array", "maxItems": 256, "items": {"type": "string"}},
            "changed_paths": {"type": "array", "maxItems": 256, "items": {"type": "string"}},
            "validation": {"type": "array", "maxItems": 96, "items": {"type": "object"}},
            "risks": {"type": "array", "maxItems": 64, "items": {"type": "string"}},
            "next_action": {"type": "string", "minLength": 1, "maxLength": 4000},
            "retry_budget": {"type": "integer", "minimum": 0, "maximum": 2},
            "previous": {"type": ["string", "null"], "maxLength": 32},
        },
    }
    return [
        {
            "name": "checkpoint_validate",
            "description": "Validate a compact native Codex MoA checkpoint without writing it.",
            "inputSchema": checkpoint_schema,
            "annotations": {"readOnlyHint": True},
        },
        {
            "name": "checkpoint_put",
            "description": "Store one immutable validated milestone checkpoint and return its opaque handle.",
            "inputSchema": checkpoint_schema,
            "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
        },
        {
            "name": "checkpoint_get",
            "description": "Read one immutable checkpoint by opaque handle.",
            "inputSchema": {
                "type": "object",
                "required": ["handle"],
                "additionalProperties": False,
                "properties": {"handle": {"type": "string", "pattern": "^[a-f0-9]{32}$"}},
            },
            "annotations": {"readOnlyHint": True},
        },
        {
            "name": "checkpoint_list",
            "description": "List compact checkpoint summaries, optionally filtered by run_id.",
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "run_id": {"type": "string", "maxLength": 128},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                },
            },
            "annotations": {"readOnlyHint": True},
        },
    ]


def _tool_result(value: Any, *, is_error: bool = False) -> dict[str, Any]:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    result: dict[str, Any] = {
        "content": [{"type": "text", "text": text}],
        "structuredContent": value,
    }
    if is_error:
        result["isError"] = True
    return result


def call_tool(store: CheckpointStore, name: str, arguments: Any) -> dict[str, Any]:
    if not isinstance(arguments, Mapping):
        return _tool_result({"error": "tool arguments must be an object"}, is_error=True)
    try:
        if name == "checkpoint_validate":
            clean = validate_checkpoint(arguments)
            return _tool_result({"valid": True, "digest": checkpoint_digest(clean), "checkpoint": clean})
        if name == "checkpoint_put":
            record, created = store.put(arguments)
            return _tool_result(
                {
                    "handle": record["handle"],
                    "digest": record["digest"],
                    "created_at": record["created_at"],
                    "created": created,
                }
            )
        if name == "checkpoint_get":
            handle = arguments.get("handle")
            if not isinstance(handle, str):
                raise StoreError("handle must be a string")
            return _tool_result(store.get(handle))
        if name == "checkpoint_list":
            run_id = arguments.get("run_id")
            limit = arguments.get("limit", 20)
            return _tool_result({"checkpoints": store.list(run_id=run_id, limit=limit)})
        return _tool_result({"error": f"unknown tool {name!r}"}, is_error=True)
    except (CheckpointError, StoreError, OSError) as exc:
        return _tool_result({"error": str(exc)}, is_error=True)


def handle_request(store: CheckpointStore, message: Any) -> dict[str, Any] | None:
    if not isinstance(message, Mapping):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}
    request_id = message.get("id")
    method = message.get("method")
    if not isinstance(method, str):
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32600, "message": "Invalid Request"}}
    if "id" not in message:
        return None
    params = message.get("params", {})
    if not isinstance(params, Mapping):
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "Invalid params"}}
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": "Store compact milestone evidence only. Never include credentials, tokens, or account data.",
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tool_definitions()}}
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str):
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "tool name is required"}}
        return {"jsonrpc": "2.0", "id": request_id, "result": call_tool(store, name, arguments)}
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def _read_message(stream: BinaryIO) -> tuple[Any | None, str]:
    first = stream.readline(MAX_MESSAGE_BYTES + 1)
    if not first:
        return None, "eof"
    if len(first) > MAX_MESSAGE_BYTES:
        raise StoreError("MCP message exceeds safety limit")
    if first.lower().startswith(b"content-length:"):
        try:
            length = int(first.split(b":", 1)[1].strip())
        except (ValueError, IndexError) as exc:
            raise StoreError("invalid Content-Length header") from exc
        if not 0 <= length <= MAX_MESSAGE_BYTES:
            raise StoreError("MCP message length exceeds safety limit")
        while True:
            header = stream.readline(8192)
            if header in (b"\n", b"\r\n", b""):
                break
        payload = stream.read(length)
        if len(payload) != length:
            raise StoreError("truncated MCP message")
        return json.loads(payload.decode("utf-8")), "framed"
    return json.loads(first.decode("utf-8")), "line"


def _write_message(stream: BinaryIO, message: Mapping[str, Any], mode: str) -> None:
    payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if mode == "framed":
        stream.write(f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii"))
        stream.write(payload)
    else:
        stream.write(payload + b"\n")
    stream.flush()


def serve_stdio(store: CheckpointStore) -> int:
    input_stream = sys.stdin.buffer
    output_stream = sys.stdout.buffer
    while True:
        try:
            message, mode = _read_message(input_stream)
            if mode == "eof":
                return 0
            response = handle_request(store, message)
            if response is not None:
                _write_message(output_stream, response, mode)
        except json.JSONDecodeError as exc:
            _write_message(
                output_stream,
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {exc}"}},
                "line",
            )
        except (StoreError, OSError) as exc:
            _write_message(
                output_stream,
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(exc)}},
                "line",
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdio", action="store_true", help="serve MCP over standard input/output")
    parser.add_argument("--store", type=Path, help="override checkpoint storage directory for tests")
    args = parser.parse_args()
    if not args.stdio:
        parser.error("only --stdio is supported")
    return serve_stdio(CheckpointStore(args.store))


if __name__ == "__main__":
    raise SystemExit(main())
