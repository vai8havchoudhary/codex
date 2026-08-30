from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PLUGIN_ROOT / "scripts" / "preflight.py"
SPEC = importlib.util.spec_from_file_location("codex_moa_preflight_test", MODULE_PATH)
assert SPEC and SPEC.loader
preflight = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = preflight
SPEC.loader.exec_module(preflight)


class PreflightTests(unittest.TestCase):
    def _files(self, root: Path, openai_ids: list[str], codex_ids: list[str]) -> tuple[Path, Path]:
        openai = root / "models.json"
        codex = root / "codex-models.json"
        openai.write_text(json.dumps({"data": [{"id": value} for value in openai_ids]}))
        codex.write_text(json.dumps({"models": [{"slug": value} for value in codex_ids]}))
        return openai, codex

    def _config(self, root: Path, gemini: str = "gemini-3.7-flash-high") -> Path:
        path = root / "config.toml"
        path.write_text(
            f'''[model_providers.cliproxyapi]\nname = "CLIProxyAPI"\nbase_url = "http://127.0.0.1:8317/v1"\nenv_key = "CLIPROXY_API_KEY"\nwire_api = "responses"\nrequires_openai_auth = false\n\n[profiles.cliproxy-grok-4-6]\nmodel = "grok-4.6"\nmodel_provider = "cliproxyapi"\n\n[profiles.cliproxy-gemini-3-7-flash]\nmodel = "{gemini}"\nmodel_provider = "cliproxyapi"\n'''
        )
        return path

    def test_vps2_ambiguity_refuses_automatic_and_explicit_high_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ids = ["grok-4.6", "gemini-3.7-flash-high", "gemini-3.7-flash-advisor"]
            openai, codex = self._files(root, ids, ids)
            config = self._config(root)
            with self.assertRaisesRegex(preflight.PreflightError, "multiple possible aliases"):
                preflight.run_preflight(
                    url="http://127.0.0.1:8317",
                    config=config,
                    grok_model=None,
                    gemini_model=None,
                    models_response_file=openai,
                    codex_models_response_file=codex,
                    timeout=1,
                )
            result = preflight.run_preflight(
                url="http://127.0.0.1:8317",
                config=config,
                grok_model=None,
                gemini_model="gemini-3.7-flash-high",
                models_response_file=openai,
                codex_models_response_file=codex,
                timeout=1,
            )
            self.assertEqual(result.grok_model, "grok-4.6")
            self.assertEqual(result.gemini_model, "gemini-3.7-flash-high")
            self.assertEqual(result.provider_id, "cliproxyapi")

    def test_explicit_alias_must_appear_in_both_catalogs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            openai, codex = self._files(
                root,
                ["grok-4.6", "gemini-3.7-flash-high"],
                ["grok-4.6", "gemini-3.7-flash-advisor"],
            )
            with self.assertRaisesRegex(preflight.PreflightError, "both CLIProxyAPI catalogs"):
                preflight.run_preflight(
                    url="http://127.0.0.1:8317",
                    config=self._config(root),
                    grok_model=None,
                    gemini_model="gemini-3.7-flash-high",
                    models_response_file=openai,
                    codex_models_response_file=codex,
                    timeout=1,
                )

    def test_configured_profile_must_equal_live_explicit_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ids = ["grok-4.6", "gemini-3.7-flash-high"]
            openai, codex = self._files(root, ids, ids)
            with self.assertRaisesRegex(preflight.PreflightError, "points to"):
                preflight.run_preflight(
                    url="http://127.0.0.1:8317",
                    config=self._config(root, "gemini-3.7-flash-advisor"),
                    grok_model=None,
                    gemini_model="gemini-3.7-flash-high",
                    models_response_file=openai,
                    codex_models_response_file=codex,
                    timeout=1,
                )


    def test_loopback_hostname_and_address_are_equivalent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ids = ["grok-4.6", "gemini-3.7-flash-high"]
            openai, codex = self._files(root, ids, ids)
            config = self._config(root)
            config.write_text(config.read_text().replace("127.0.0.1", "localhost"))
            result = preflight.run_preflight(
                url="http://127.0.0.1:8317",
                config=config,
                grok_model=None,
                gemini_model="gemini-3.7-flash-high",
                models_response_file=openai,
                codex_models_response_file=codex,
                timeout=1,
            )
            self.assertEqual(result.provider_id, "cliproxyapi")

    def test_non_loopback_plain_http_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ids = ["grok-4.6", "gemini-3.7-flash-high"]
            openai, codex = self._files(root, ids, ids)
            with self.assertRaisesRegex(preflight.PreflightError, "plain HTTP"):
                preflight.run_preflight(
                    url="http://example.com:8317",
                    config=self._config(root),
                    grok_model=None,
                    gemini_model="gemini-3.7-flash-high",
                    models_response_file=openai,
                    codex_models_response_file=codex,
                    timeout=1,
                )


if __name__ == "__main__":
    unittest.main()
