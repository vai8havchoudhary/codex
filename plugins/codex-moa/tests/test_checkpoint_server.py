from __future__ import annotations

import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = PLUGIN_ROOT / "mcp" / "server.py"
SPEC = importlib.util.spec_from_file_location("codex_moa_mcp_server_test", SERVER_PATH)
assert SPEC and SPEC.loader
server = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = server
SPEC.loader.exec_module(server)


def checkpoint(**overrides):
    value = {
        "schema_version": 2,
        "council": "grok-gemini",
        "run_id": "repo-repair-1",
        "objective": "Repair the repository with one coherent native plugin tree.",
        "phase": "implement",
        "status": "active",
        "leader_mode": "grok-gemini",
        "leader_model": "grok-4.6",
        "advisor_models": ["gemini-3.7-flash-high"],
        "constraints": ["one writer", "no release tag"],
        "decisions": ["use native Codex subagents"],
        "evidence": [{"kind": "test", "summary": "focused gate passed", "command": "python3 -m unittest", "exit_code": 0}],
        "owned_paths": ["plugins/codex-moa"],
        "changed_paths": ["plugins/codex-moa/mcp/server.py"],
        "validation": [{"command": "python3 -m unittest", "status": "pass", "summary": "tests passed", "exit_code": 0}],
        "risks": [],
        "next_action": "Run repository gates.",
        "retry_budget": 2,
        "previous": None,
    }
    value.update(overrides)
    return value


class StoreTests(unittest.TestCase):
    def test_put_get_list_permissions_and_idempotence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "store"
            store = server.CheckpointStore(root)
            first, created = store.put(checkpoint())
            self.assertTrue(created)
            second, created_again = store.put(checkpoint())
            self.assertFalse(created_again)
            self.assertEqual(first["handle"], second["handle"])
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
            checkpoint_path = root / f"{first['handle']}.json"
            self.assertEqual(stat.S_IMODE(checkpoint_path.stat().st_mode), 0o600)
            loaded = store.get(first["handle"])
            self.assertEqual(loaded["checkpoint"]["run_id"], "repo-repair-1")
            summaries = store.list(run_id="repo-repair-1", limit=10)
            self.assertEqual([item["handle"] for item in summaries], [first["handle"]])
            self.assertNotIn("evidence", summaries[0])

    def test_previous_checkpoint_must_exist_and_match_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = server.CheckpointStore(Path(tmp) / "store")
            first, _ = store.put(checkpoint())
            followup, created = store.put(
                checkpoint(phase="validate", previous=first["handle"], next_action="Review the diff.")
            )
            self.assertTrue(created)
            self.assertEqual(followup["checkpoint"]["previous"], first["handle"])
            with self.assertRaisesRegex(server.StoreError, "different run_id"):
                store.put(checkpoint(run_id="other-run", previous=first["handle"]))

    def test_secret_fields_and_values_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = server.CheckpointStore(Path(tmp) / "store")
            bad = checkpoint()
            bad["api_key"] = "fixture"
            with self.assertRaisesRegex(server.StoreError, "unsupported fields|sensitive"):
                store.put(bad)
            with self.assertRaisesRegex(server.StoreError, "secret value"):
                store.put(checkpoint(next_action="Use Bearer not-a-real-secret-fixture-value"))

    def test_relative_store_path_is_refused(self) -> None:
        with self.assertRaisesRegex(server.StoreError, "absolute path"):
            server.CheckpointStore(Path("relative/checkpoints"))

    def test_record_limit_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = server.CheckpointStore(Path(tmp) / "store")
            original = server.MAX_CHECKPOINTS
            server.MAX_CHECKPOINTS = 1
            try:
                store.put(checkpoint())
                with self.assertRaisesRegex(server.StoreError, "safety limit"):
                    store.put(checkpoint(phase="validate", next_action="Review."))
            finally:
                server.MAX_CHECKPOINTS = original

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_symlink_store_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real"
            real.mkdir()
            link = root / "link"
            link.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(server.StoreError, "symlink"):
                server.CheckpointStore(link).put(checkpoint())


class ProtocolTests(unittest.TestCase):
    def test_tools_are_native_checkpoint_only(self) -> None:
        names = [tool["name"] for tool in server.tool_definitions()]
        self.assertEqual(
            names,
            ["checkpoint_validate", "checkpoint_put", "checkpoint_get", "checkpoint_list"],
        )
        joined = json.dumps(server.tool_definitions()).lower()
        for forbidden in ("spawn model", "hermes", "account route", "shell command"):
            self.assertNotIn(forbidden, joined)

    def test_json_rpc_round_trip_over_stdio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            process = subprocess.Popen(
                [sys.executable, str(SERVER_PATH), "--stdio", "--store", str(Path(tmp) / "store")],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            assert process.stdin and process.stdout
            requests = [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "checkpoint_put", "arguments": checkpoint()}},
            ]
            responses = []
            for request in requests:
                process.stdin.write(json.dumps(request) + "\n")
                process.stdin.flush()
                responses.append(json.loads(process.stdout.readline()))
            process.stdin.close()
            process.wait(timeout=5)
            process.stdout.close()
            assert process.stderr is not None
            process.stderr.close()
            self.assertEqual(process.returncode, 0)
            self.assertEqual(responses[0]["result"]["serverInfo"]["name"], "codex-moa-checkpoints")
            self.assertEqual(len(responses[1]["result"]["tools"]), 4)
            self.assertRegex(responses[2]["result"]["structuredContent"]["handle"], r"^[a-f0-9]{32}$")


if __name__ == "__main__":
    unittest.main()
