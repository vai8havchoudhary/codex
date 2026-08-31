from __future__ import annotations

import contextlib
import http.server
import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
import threading
import tomllib
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
MODULE_PATH = SCRIPT_DIR / "install.py"
SPEC = importlib.util.spec_from_file_location("cliproxy_install_transaction", MODULE_PATH)
assert SPEC and SPEC.loader
install = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = install
SPEC.loader.exec_module(install)
config_edit = sys.modules["config_edit"]
config_transaction = sys.modules["config_transaction"]


class CatalogHandler(http.server.BaseHTTPRequestHandler):
    token = "secret-token"
    requests: list[str] = []

    def do_GET(self):
        type(self).requests.append(self.path)
        if self.headers.get("Authorization") != f"Bearer {self.token}":
            self.send_response(401)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        ids = ["grok-4.6", "gemini-3.7-flash-high", "gpt-5.6-luna"]
        if "client_version=" in self.path:
            payload = {"models": [{"slug": value} for value in ids]}
        else:
            payload = {"data": [{"id": value} for value in ids]}
        self.wfile.write(json.dumps(payload).encode())

    def log_message(self, *_args):
        return


class EndToEndTests(unittest.TestCase):
    def _offline_files(self, root: Path) -> tuple[Path, Path]:
        ids = ["grok-4.6", "gemini-3.7-flash-high", "gpt-5.6-luna"]
        openai = root / "openai.json"
        codex = root / "codex.json"
        openai.write_text(json.dumps({"data": [{"id": value} for value in ids]}))
        codex.write_text(json.dumps({"models": [{"slug": value} for value in ids]}))
        return openai, codex

    def _args(self, config: Path, openai: Path, codex: Path) -> list[str]:
        return [
            "--config",
            str(config),
            "--models-response-file",
            str(openai),
            "--codex-models-response-file",
            str(codex),
            "--gemini-model",
            "gemini-3.7-flash-high",
            "--default",
            "grok",
        ]

    def test_live_auth_backups_permissions_idempotence_and_no_secret(self):
        CatalogHandler.requests = []
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), CatalogHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        old = os.environ.get("CLIPROXY_API_KEY")
        os.environ["CLIPROXY_API_KEY"] = CatalogHandler.token
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                config = root / "config.toml"
                config.write_text('model = "grok-4.6"\nmodel_provider = "openai"\n')
                args = [
                    "--config",
                    str(config),
                    "--base-url",
                    f"http://127.0.0.1:{server.server_port}/v1",
                    "--api-key-env",
                    "CLIPROXY_API_KEY",
                    "--gemini-model",
                    "gemini-3.7-flash-high",
                ]
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(install.main(args), 0)
                paths = [
                    config,
                    config_edit.profile_path(config, install.GROK_PROFILE),
                    config_edit.profile_path(config, install.GEMINI_PROFILE),
                ]
                first = [path.read_text() for path in paths]
                for path in paths:
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                    self.assertNotIn(CatalogHandler.token, path.read_text())
                self.assertIn('env_key = "CLIPROXY_API_KEY"', first[0])
                backups = list(root.glob("*.bak.*"))
                self.assertEqual(len(backups), 1)
                self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(install.main(args), 0)
                self.assertEqual([path.read_text() for path in paths], first)
                self.assertEqual(list(root.glob("*.bak.*")), backups)
                self.assertEqual(len(CatalogHandler.requests), 4)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
            if old is None:
                os.environ.pop("CLIPROXY_API_KEY", None)
            else:
                os.environ["CLIPROXY_API_KEY"] = old

    def test_migration_creates_three_profile_compatible_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            openai, codex = self._offline_files(root)
            config.write_text(
                f'''profile = "{install.GROK_PROFILE}"
{install.BEGIN}
[model_providers.cliproxyapi]
name = "CLIProxyAPI"
base_url = "http://127.0.0.1:8317/v1"
wire_api = "responses"
requires_openai_auth = false

[profiles.{install.GROK_PROFILE}]
model = "grok-4.6"
model_provider = "cliproxyapi"

[profiles.{install.GEMINI_PROFILE}]
model = "gemini-3.7-flash-high"
model_provider = "cliproxyapi"
{install.END}
'''
            )
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(install.main(self._args(config, openai, codex)), 0)
            base = tomllib.loads(config.read_text())
            self.assertNotIn("profile", base)
            self.assertNotIn("profiles", base)
            for name, model in (
                (install.GROK_PROFILE, "grok-4.6"),
                (install.GEMINI_PROFILE, "gemini-3.7-flash-high"),
            ):
                overlay = tomllib.loads(
                    config_edit.profile_path(config, name).read_text()
                )
                self.assertEqual(
                    overlay,
                    {"model": model, "model_provider": "cliproxyapi"},
                )

    def test_existing_profile_files_are_backed_up_and_unrelated_settings_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            openai, codex = self._offline_files(root)
            config.write_text('model = "grok-4.6"\n')
            grok = config_edit.profile_path(config, install.GROK_PROFILE)
            gemini = config_edit.profile_path(config, install.GEMINI_PROFILE)
            grok.write_text('approval_policy = "on-request" # keep\n')
            gemini.write_text('sandbox_mode = "workspace-write" # keep\n')
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(install.main(self._args(config, openai, codex)), 0)
            self.assertIn("# keep", grok.read_text())
            self.assertIn("# keep", gemini.read_text())
            backups = list(root.glob("*.bak.*"))
            self.assertEqual(len(backups), 3)
            self.assertTrue(all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in backups))

    def test_transaction_rolls_back_all_files_after_partial_write_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            openai, codex = self._offline_files(root)
            config.write_text('model = "grok-4.6"\nmodel_provider = "openai"\n')
            os.chmod(config, 0o640)
            before = config.read_bytes()
            original_replace = config_transaction._replace_text
            target = config_edit.profile_path(config, install.GEMINI_PROFILE)
            failed = False

            def failing_replace(path: Path, content: str, mode: int) -> None:
                nonlocal failed
                if path == target and not failed:
                    failed = True
                    raise OSError("injected profile write failure")
                original_replace(path, content, mode)

            config_transaction._replace_text = failing_replace
            err = io.StringIO()
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                    code = install.main(self._args(config, openai, codex))
            finally:
                config_transaction._replace_text = original_replace
            self.assertEqual(code, 2)
            self.assertIn("rolled back", err.getvalue())
            self.assertEqual(config.read_bytes(), before)
            self.assertEqual(stat.S_IMODE(config.stat().st_mode), 0o640)
            self.assertFalse(config_edit.profile_path(config, install.GROK_PROFILE).exists())
            self.assertFalse(target.exists())
            self.assertFalse(list(root.glob("*.bak.*")))

    def test_symlink_profile_is_refused_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            openai, codex = self._offline_files(root)
            config.write_text('model = "grok-4.6"\n')
            target = root / "target.toml"
            target.write_text("user = true\n")
            config_edit.profile_path(config, install.GROK_PROFILE).symlink_to(target)
            err = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                code = install.main(self._args(config, openai, codex))
            self.assertEqual(code, 2)
            self.assertIn("symlink", err.getvalue())
            self.assertEqual(target.read_text(), "user = true\n")
            self.assertNotIn("model_providers", config.read_text())

    def test_preserve_refuses_model_absent_from_proxy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            openai, codex = self._offline_files(root)
            config.write_text('model = "gpt-not-exported"\nmodel_provider = "openai"\n')
            err = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                code = install.main(
                    [
                        "--config",
                        str(config),
                        "--models-response-file",
                        str(openai),
                        "--codex-models-response-file",
                        str(codex),
                        "--gemini-model",
                        "gemini-3.7-flash-high",
                    ]
                )
            self.assertEqual(code, 2)
            self.assertIn("not published", err.getvalue())
            self.assertEqual(tomllib.loads(config.read_text())["model_provider"], "openai")
            self.assertFalse(config_edit.profile_path(config, install.GROK_PROFILE).exists())


if __name__ == "__main__":
    unittest.main()
