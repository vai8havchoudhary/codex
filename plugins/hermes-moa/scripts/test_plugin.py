from __future__ import annotations

import contextlib
import http.server
import importlib.util
import io
import json
import os
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("plugin.py")
SPEC = importlib.util.spec_from_file_location("hermes_moa_plugin", MODULE_PATH)
assert SPEC and SPEC.loader
plugin = importlib.util.module_from_spec(SPEC)
import sys
sys.path.insert(0, str(MODULE_PATH.parent))
sys.modules[SPEC.name] = plugin
SPEC.loader.exec_module(plugin)

SECRET = "not-a-real-secret-fixture"


FAKE_HERMES = r'''#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
profile = None
if len(args) >= 2 and args[0] == "-p":
    profile = args[1]
    args = args[2:]
base = Path(os.environ["HERMES_HOME"])
if profile:
    base = base / "profiles" / profile
config = base / "config.yaml"
base.mkdir(parents=True, exist_ok=True)

def load():
    if not config.exists() or not config.read_text().strip():
        return {}
    return json.loads(config.read_text())

def save(data):
    config.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n")
    os.chmod(config, 0o600)

def get(data, key):
    cur = data
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(key)
        cur = cur[part]
    return cur

def set_value(data, key, value):
    cur = data
    parts = key.split(".")
    for part in parts[:-1]:
        next_value = cur.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            cur[part] = next_value
        cur = next_value
    lower = value.lower()
    if value.lstrip().startswith(("[", "{")):
        parsed = json.loads(value)
    elif lower == "true":
        parsed = True
    elif lower == "false":
        parsed = False
    else:
        try:
            parsed = int(value)
        except ValueError:
            parsed = value
    cur[parts[-1]] = parsed

def unset(data, key):
    cur = data
    parts = key.split(".")
    for part in parts[:-1]:
        if not isinstance(cur, dict) or part not in cur:
            return
        cur = cur[part]
    if isinstance(cur, dict):
        cur.pop(parts[-1], None)

if args == ["--version"]:
    print("Hermes Agent 0.19-test")
    raise SystemExit(0)
if args[:2] == ["moa", "list"]:
    data = load()
    presets = data.get("moa", {}).get("presets", {})
    for name in sorted(presets):
        print(name)
    raise SystemExit(0)
if args[:2] == ["config", "get"]:
    key = args[2]
    try:
        value = get(load(), key)
    except KeyError:
        print(f"Config key not set: {key}", file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(value))
    raise SystemExit(0)
if args[:2] == ["config", "set"]:
    key, value = args[2], args[3]
    if os.environ.get("FAKE_HERMES_FAIL_KEY") == key:
        print(f"forced failure for {key}", file=sys.stderr)
        raise SystemExit(9)
    data = load()
    set_value(data, key, value)
    save(data)
    raise SystemExit(0)
if args[:2] == ["config", "unset"]:
    data = load()
    unset(data, args[2])
    save(data)
    raise SystemExit(0)
if args[:2] == ["config", "check"]:
    raise SystemExit(0)
print("unknown fake hermes command: " + " ".join(args), file=sys.stderr)
raise SystemExit(2)
'''


class CatalogHandler(http.server.BaseHTTPRequestHandler):
    requests: list[str] = []

    def do_GET(self):
        type(self).requests.append(self.path)
        if self.headers.get("Authorization") != f"Bearer {SECRET}":
            self.send_response(401)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if "client_version=" in self.path:
            payload = {
                "models": [
                    {"slug": "xai/grok-4.6"},
                    {"slug": "google/gemini-3.7-flash"},
                ]
            }
        else:
            payload = {
                "data": [
                    {"id": "xai/grok-4.6"},
                    {"id": "google/gemini-3.7-flash"},
                ]
            }
        self.wfile.write(json.dumps(payload).encode())

    def log_message(self, *_args):
        return


class Harness(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "hermes-home"
        self.fake = self.root / "hermes"
        self.fake.write_text(FAKE_HERMES)
        self.fake.chmod(0o755)
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), CatalogHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        CatalogHandler.requests = []
        self.env = patch.dict(
            os.environ,
            {
                "CLIPROXY_API_KEY": SECRET,
                "CLIPROXY_URL": f"http://127.0.0.1:{self.server.server_port}",
            },
            clear=False,
        )
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    @property
    def config(self) -> Path:
        return self.home / "config.yaml"

    def invoke(self, *args: str) -> tuple[int, str, str]:
        out = io.StringIO()
        err = io.StringIO()
        argv = [
            "--hermes-bin",
            str(self.fake),
            "--home",
            str(self.home),
            *args,
        ]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = plugin.main(argv)
        return code, out.getvalue(), err.getvalue()


class HermesMoATests(Harness):
    def test_setup_creates_two_presets_without_persisting_secret_and_is_idempotent(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text(json.dumps({"terminal": {"backend": "local"}}) + "\n")
        code, out, err = self.invoke("setup", "grok-led")
        self.assertEqual((code, err), (0, ""))
        state = json.loads(self.config.read_text())
        self.assertEqual(state["providers"]["cliproxy"]["api"], f"http://127.0.0.1:{self.server.server_port}/v1")
        self.assertEqual(state["providers"]["cliproxy"]["key_env"], "CLIPROXY_API_KEY")
        self.assertEqual(state["providers"]["cliproxy"]["transport"], "openai_chat")
        self.assertEqual(state["moa"]["default_preset"], "cliproxy-grok-led")
        self.assertEqual(state["model"], {"default": "cliproxy-grok-led", "provider": "moa"})
        self.assertEqual(state["moa"]["privacy_filter"], "display")
        grok = state["moa"]["presets"]["cliproxy-grok-led"]
        gemini = state["moa"]["presets"]["cliproxy-gemini-led"]
        self.assertEqual(grok["aggregator"], {"provider": "cliproxy", "model": "xai/grok-4.6"})
        self.assertEqual(gemini["aggregator"], {"provider": "cliproxy", "model": "google/gemini-3.7-flash"})
        self.assertEqual(
            grok["reference_models"],
            [{"enabled": True, "model": "google/gemini-3.7-flash", "provider": "cliproxy"}],
        )
        self.assertEqual(grok["reference_max_tokens"], 600)
        self.assertEqual(grok["fanout"], "user_turn")
        self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o600)
        combined = out + err + self.config.read_text()
        self.assertNotIn(SECRET, combined)
        backups = list(self.config.parent.glob("config.yaml.bak.cliproxy-moa.*"))
        self.assertEqual(len(backups), 1)
        first = self.config.read_bytes()

        code, out, err = self.invoke("setup", "grok-led")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("already up to date", out)
        self.assertEqual(self.config.read_bytes(), first)
        self.assertEqual(list(self.config.parent.glob("config.yaml.bak.cliproxy-moa.*")), backups)
        self.assertEqual(len(CatalogHandler.requests), 4)

    def test_owned_presets_can_update_tuning_without_force(self):
        code, _, err = self.invoke("setup", "grok-led")
        self.assertEqual((code, err), (0, ""))
        code, _, err = self.invoke(
            "setup", "gemini-led", "--reference-max-tokens", "700", "--fanout", "every_n:2"
        )
        self.assertEqual((code, err), (0, ""))
        state = json.loads(self.config.read_text())
        for preset in state["moa"]["presets"].values():
            self.assertEqual(preset["reference_max_tokens"], 700)
            self.assertEqual(preset["fanout"], "every_n:2")
        self.assertEqual(state["moa"]["default_preset"], "cliproxy-gemini-led")

    def test_use_switches_to_gemini_led_after_setup(self):
        code, _, err = self.invoke("setup", "grok-led")
        self.assertEqual((code, err), (0, ""))
        code, out, err = self.invoke("use", "gemini-led")
        self.assertEqual((code, err), (0, ""))
        state = json.loads(self.config.read_text())
        self.assertEqual(state["model"], {"default": "cliproxy-gemini-led", "provider": "moa"})
        self.assertEqual(state["moa"]["default_preset"], "cliproxy-gemini-led")
        self.assertIn("cliproxy-gemini-led", out)

    def test_status_is_read_only_and_detects_exact_route(self):
        code, _, err = self.invoke("setup", "grok-led")
        self.assertEqual((code, err), (0, ""))
        before = self.config.read_bytes()
        code, out, err = self.invoke("status")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("Configured: yes", out)
        self.assertIn("Active MoA: yes", out)
        self.assertEqual(self.config.read_bytes(), before)

    def test_collision_refuses_without_force(self):
        self.config.parent.mkdir(parents=True)
        original = {
            "providers": {
                "cliproxy": {
                    "api": "https://other.example/v1",
                    "key_env": "OTHER_KEY",
                    "transport": "openai_chat",
                }
            }
        }
        self.config.write_text(json.dumps(original) + "\n")
        before = self.config.read_bytes()
        code, _, err = self.invoke("setup", "grok-led")
        self.assertEqual(code, 2)
        self.assertIn("refusing to overwrite", err)
        self.assertEqual(self.config.read_bytes(), before)

    def test_failure_rolls_back_exact_original_bytes(self):
        self.config.parent.mkdir(parents=True)
        original = b'{"terminal":{"backend":"local"}}\n'
        self.config.write_bytes(original)
        with patch.dict(
            os.environ,
            {"FAKE_HERMES_FAIL_KEY": "moa.presets.cliproxy-gemini-led"},
            clear=False,
        ):
            code, _, err = self.invoke("setup", "grok-led")
        self.assertEqual(code, 2)
        self.assertIn("forced failure", err)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertEqual(list(self.config.parent.glob("config.yaml.bak.cliproxy-moa.*")), [])

    def test_preserves_stronger_full_privacy_filter(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text(json.dumps({"moa": {"privacy_filter": "full"}}) + "\n")
        code, _, err = self.invoke("setup", "grok-led")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(self.config.read_text())["moa"]["privacy_filter"], "full")

    def test_profile_targets_profile_home(self):
        code, _, err = self.invoke("--profile", "coder", "setup", "gemini-led")
        self.assertEqual((code, err), (0, ""))
        profile_config = self.home / "profiles" / "coder" / "config.yaml"
        self.assertTrue(profile_config.is_file())
        state = json.loads(profile_config.read_text())
        self.assertEqual(state["model"]["default"], "cliproxy-gemini-led")


class AdmissionTests(unittest.TestCase):
    def test_rejects_non_loopback_plain_http(self):
        with self.assertRaises(plugin.CatalogError):
            plugin.normalize_base_url("http://proxy.example.com:8317")

    def test_rejects_nearby_or_ambiguous_aliases(self):
        Catalogs = plugin.read_catalogs.__globals__["Catalogs"]
        with self.assertRaises(plugin.CatalogError):
            plugin.resolve_models(
                Catalogs(
                    ("grok-4.60", "gemini-3.7-flash"),
                    ("grok-4.60", "gemini-3.7-flash"),
                )
            )
        with self.assertRaisesRegex(plugin.CatalogError, "multiple possible aliases"):
            plugin.resolve_models(
                Catalogs(
                    ("grok-4.6", "xai/grok-4.6", "gemini-3.7-flash"),
                    ("grok-4.6", "xai/grok-4.6", "gemini-3.7-flash"),
                )
            )


if __name__ == "__main__":
    unittest.main()
