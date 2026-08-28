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

MODULE_PATH = Path(__file__).with_name("install.py")
SPEC = importlib.util.spec_from_file_location("cliproxy_install", MODULE_PATH)
assert SPEC and SPEC.loader
install = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = install
SPEC.loader.exec_module(install)


def catalogs(openai: list[str], codex: list[str] | None = None):
    return install.Catalogs(tuple(openai), tuple(codex or openai))


class CatalogTests(unittest.TestCase):
    def test_extracts_openai_and_codex_shapes(self):
        self.assertEqual(install.extract_openai_ids({"data": [{"id": "grok-4.6"}]}), ("grok-4.6",))
        self.assertEqual(install.extract_codex_slugs({"models": [{"slug": "gemini-3.7-flash"}]}), ("gemini-3.7-flash",))

    def test_resolves_namespaced_exact_aliases(self):
        result = install.resolve_models(catalogs(["xai/grok-4.6", "google/gemini-3.7-flash"]))
        self.assertEqual(result, install.Models("xai/grok-4.6", "google/gemini-3.7-flash"))

    def test_rejects_nearby_versions_and_markerless_gemini(self):
        for values in (["grok-4.60", "gemini-3.7-flash"], ["grok-4.6.1", "gemini-3.7-flash"], ["grok-4.6", "gemini-3.70-flash"], ["grok-4.6", "gemini-3.7"]):
            with self.subTest(values=values), self.assertRaises(install.InstallError):
                install.resolve_models(catalogs(values))

    def test_requires_alias_in_both_catalogs(self):
        with self.assertRaisesRegex(install.InstallError, "both catalogs"):
            install.resolve_models(catalogs(["grok-4.6", "gemini-3.7-flash"], ["grok-4.6"]))

    def test_ambiguity_requires_explicit_alias(self):
        values = ["grok-4.6", "xai/grok-4.6", "gemini-3.7-flash"]
        with self.assertRaisesRegex(install.InstallError, "multiple possible aliases"):
            install.resolve_models(catalogs(values))
        result = install.resolve_models(catalogs(values), grok="xai/grok-4.6")
        self.assertEqual(result.grok, "xai/grok-4.6")

    def test_offline_requires_both_catalog_shapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "models.json"
            path.write_text(json.dumps({"data": [{"id": "grok-4.6"}]}))
            with self.assertRaisesRegex(install.InstallError, "also requires"):
                install.read_catalogs("http://127.0.0.1:8317/v1", None, path, None, 1)


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.provider = install.Provider("cliproxyapi", "CLIProxyAPI", "http://127.0.0.1:8317/v1", "CLIPROXY_API_KEY", True)
        self.models = install.Models("grok-4.6", "gemini-3.7-flash")

    def test_reuses_one_existing_provider_and_preserves_env_key(self):
        parsed = tomllib.loads('''[model_providers.proxy]\nname = "CLIProxyAPI"\nbase_url = "http://localhost:8317/v1"\nenv_key = "EXISTING_TOKEN"\n''')
        provider = install.choose_provider(parsed, "cliproxyapi", "http://127.0.0.1:8317/v1", None)
        self.assertEqual(provider.provider_id, "proxy")
        self.assertEqual(provider.env_key, "EXISTING_TOKEN")
        self.assertFalse(provider.is_new)

    def test_refuses_unrelated_provider_collision(self):
        parsed = tomllib.loads('''[model_providers.cliproxyapi]\nname = "Other"\nbase_url = "https://example.com/v1"\n''')
        with self.assertRaisesRegex(install.InstallError, "unrelated"):
            install.choose_provider(parsed, "cliproxyapi", "http://127.0.0.1:8317/v1", None)

    def test_render_preserves_comments_arrays_and_is_idempotent(self):
        original = 'model = "grok-4.6" # keep\n\n[[hooks]]\ncommand = "echo ok"\n'
        rendered = install.render_config(original, self.provider, self.models, True, None)
        parsed = tomllib.loads(rendered)
        self.assertEqual(parsed["model_provider"], "cliproxyapi")
        self.assertEqual(parsed["hooks"][0]["command"], "echo ok")
        self.assertIn('# keep', rendered)
        self.assertEqual(install.render_config(rendered, self.provider, self.models, True, None), rendered)

    def test_profiles_only_leaves_active_provider(self):
        original = 'model = "gpt-5.6"\nmodel_provider = "openai"\n'
        rendered = install.render_config(original, self.provider, self.models, False, None)
        self.assertEqual(tomllib.loads(rendered)["model_provider"], "openai")


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
        if "client_version=" in self.path:
            payload = {"models": [{"slug": "grok-4.6"}, {"slug": "gemini-3.7-flash"}]}
        else:
            payload = {"data": [{"id": "grok-4.6"}, {"id": "gemini-3.7-flash"}]}
        self.wfile.write(json.dumps(payload).encode())

    def log_message(self, *_args):
        return


class EndToEndTests(unittest.TestCase):
    def test_live_auth_backup_permissions_and_idempotence(self):
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
                args = ["--config", str(config), "--base-url", f"http://127.0.0.1:{server.server_port}/v1", "--api-key-env", "CLIPROXY_API_KEY"]
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(install.main(args), 0)
                first = config.read_text()
                self.assertEqual(stat.S_IMODE(config.stat().st_mode), 0o600)
                self.assertNotIn(CatalogHandler.token, first)
                self.assertIn('env_key = "CLIPROXY_API_KEY"', first)
                backups = list(root.glob("config.toml.bak.*"))
                self.assertEqual(len(backups), 1)
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(install.main(args), 0)
                self.assertEqual(config.read_text(), first)
                self.assertEqual(list(root.glob("config.toml.bak.*")), backups)
                self.assertEqual(len(CatalogHandler.requests), 4)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
            if old is None:
                os.environ.pop("CLIPROXY_API_KEY", None)
            else:
                os.environ["CLIPROXY_API_KEY"] = old

    def test_preserve_refuses_model_absent_from_proxy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            openai = root / "openai.json"
            codex = root / "codex.json"
            config.write_text('model = "gpt-not-exported"\nmodel_provider = "openai"\n')
            openai.write_text(json.dumps({"data": [{"id": "grok-4.6"}, {"id": "gemini-3.7-flash"}]}))
            codex.write_text(json.dumps({"models": [{"slug": "grok-4.6"}, {"slug": "gemini-3.7-flash"}]}))
            err = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                code = install.main(["--config", str(config), "--models-response-file", str(openai), "--codex-models-response-file", str(codex)])
            self.assertEqual(code, 2)
            self.assertIn("not published", err.getvalue())
            self.assertEqual(tomllib.loads(config.read_text())["model_provider"], "openai")


if __name__ == "__main__":
    unittest.main()
