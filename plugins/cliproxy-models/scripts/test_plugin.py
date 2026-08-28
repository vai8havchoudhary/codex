from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("plugin.py")
SPEC = importlib.util.spec_from_file_location("cliproxy_plugin", MODULE_PATH)
assert SPEC and SPEC.loader
plugin = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = plugin
SPEC.loader.exec_module(plugin)


class FakeInstaller:
    def __init__(self) -> None:
        self.args: list[str] | None = None

    def main(self, args: list[str]) -> int:
        self.args = args
        return 0


class EndpointTests(unittest.TestCase):
    def test_normalizes_root_or_v1(self) -> None:
        self.assertEqual(
            plugin.normalize_provider_base_url("http://127.0.0.1:8317"),
            "http://127.0.0.1:8317/v1",
        )
        self.assertEqual(
            plugin.normalize_provider_base_url("http://localhost:8317/v1/"),
            "http://localhost:8317/v1",
        )

    def test_rejects_unsafe_or_ambiguous_urls(self) -> None:
        for value in (
            "http://example.com:8317",
            "http://user:secret@127.0.0.1:8317",
            "http://127.0.0.1:8317/custom",
            "http://127.0.0.1:8317?token=nope",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                plugin.normalize_provider_base_url(value)


class DispatchTests(unittest.TestCase):
    def test_status_uses_exact_environment_contract_without_secret_value(self) -> None:
        fake = FakeInstaller()
        original = plugin.load_installer
        old_url = os.environ.get("CLIPROXY_URL")
        old_key = os.environ.get("CLIPROXY_API_KEY")
        os.environ["CLIPROXY_URL"] = "http://127.0.0.1:8317"
        os.environ["CLIPROXY_API_KEY"] = "not-a-real-secret-fixture"
        plugin.load_installer = lambda: fake
        try:
            self.assertEqual(plugin.main(["status"]), 0)
        finally:
            plugin.load_installer = original
            if old_url is None:
                os.environ.pop("CLIPROXY_URL", None)
            else:
                os.environ["CLIPROXY_URL"] = old_url
            if old_key is None:
                os.environ.pop("CLIPROXY_API_KEY", None)
            else:
                os.environ["CLIPROXY_API_KEY"] = old_key
        assert fake.args is not None
        self.assertIn("CLIPROXY_API_KEY", fake.args)
        self.assertNotIn("not-a-real-secret-fixture", fake.args)
        self.assertEqual(fake.args[-2:], ["--profiles-only", "--dry-run"])

    def test_setup_and_use_select_requested_default(self) -> None:
        for argv, expected in ((["setup"], "grok"), (["setup", "gemini"], "gemini"), (["use", "grok"], "grok")):
            fake = FakeInstaller()
            original = plugin.load_installer
            plugin.load_installer = lambda: fake
            try:
                self.assertEqual(plugin.main(argv), 0)
            finally:
                plugin.load_installer = original
            assert fake.args is not None
            self.assertEqual(fake.args[-2:], ["--default", expected])


if __name__ == "__main__":
    unittest.main()
