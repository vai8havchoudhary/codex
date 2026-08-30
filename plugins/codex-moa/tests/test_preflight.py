from __future__ import annotations

import tempfile
from pathlib import Path

from support import PreflightTestCase, preflight


class ModernProfilePreflightTests(PreflightTestCase):
    def test_vps2_ambiguity_refuses_automatic_and_explicit_high_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ids = ["grok-4.6", "gemini-3.7-flash-high", "gemini-3.7-flash-advisor"]
            openai, codex = self.files(root, ids, ids)
            config = self.config(root)
            with self.assertRaisesRegex(preflight.PreflightError, "multiple possible aliases"):
                preflight.run_preflight(
                    url="http://127.0.0.1:8317", config=config,
                    grok_model=None, gemini_model=None,
                    models_response_file=openai, codex_models_response_file=codex, timeout=1,
                )
            result = preflight.run_preflight(
                url="http://127.0.0.1:8317", config=config,
                grok_model=None, gemini_model="gemini-3.7-flash-high",
                models_response_file=openai, codex_models_response_file=codex, timeout=1,
            )
            self.assertEqual(result.gemini_model, "gemini-3.7-flash-high")

    def test_explicit_alias_must_appear_in_both_catalogs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            openai, codex = self.files(
                root,
                ["grok-4.6", "gemini-3.7-flash-high"],
                ["grok-4.6", "gemini-3.7-flash-advisor"],
            )
            with self.assertRaisesRegex(preflight.PreflightError, "both CLIProxyAPI catalogs"):
                preflight.run_preflight(
                    url="http://127.0.0.1:8317", config=self.config(root),
                    grok_model=None, gemini_model="gemini-3.7-flash-high",
                    models_response_file=openai, codex_models_response_file=codex, timeout=1,
                )

    def test_configured_overlay_must_equal_live_explicit_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ids = ["grok-4.6", "gemini-3.7-flash-high"]
            openai, codex = self.files(root, ids, ids)
            with self.assertRaisesRegex(preflight.PreflightError, "points to"):
                preflight.run_preflight(
                    url="http://127.0.0.1:8317",
                    config=self.config(root, gemini="gemini-3.7-flash-advisor"),
                    grok_model=None, gemini_model="gemini-3.7-flash-high",
                    models_response_file=openai, codex_models_response_file=codex, timeout=1,
                )

    def test_missing_overlay_has_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ids = ["grok-4.6", "gemini-3.7-flash-high"]
            openai, codex = self.files(root, ids, ids)
            config = self.config(root)
            preflight.profile_path(config, preflight.GEMINI_PROFILE).unlink()
            with self.assertRaisesRegex(
                preflight.PreflightError,
                r"Codex profile overlay.*is missing.*cliproxy-models setup",
            ):
                preflight.run_preflight(
                    url="http://127.0.0.1:8317", config=config,
                    grok_model="grok-4.6", gemini_model="gemini-3.7-flash-high",
                    models_response_file=openai, codex_models_response_file=codex, timeout=1,
                )

    def test_base_legacy_profile_tables_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ids = ["grok-4.6", "gemini-3.7-flash-high"]
            openai, codex = self.files(root, ids, ids)
            config = self.config(root)
            config.write_text(
                config.read_text(encoding="utf-8")
                + '\n[profiles.cliproxy-grok-4-6]\nmodel = "grok-4.6"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(preflight.PreflightError, r"legacy `\[profiles\.\*\]`"):
                preflight.run_preflight(
                    url="http://127.0.0.1:8317", config=config,
                    grok_model="grok-4.6", gemini_model="gemini-3.7-flash-high",
                    models_response_file=openai, codex_models_response_file=codex, timeout=1,
                )

    def test_profile_overlay_provider_mismatch_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ids = ["grok-4.6", "gemini-3.7-flash-high"]
            openai, codex = self.files(root, ids, ids)
            with self.assertRaisesRegex(preflight.PreflightError, "must use the same"):
                preflight.run_preflight(
                    url="http://127.0.0.1:8317",
                    config=self.config(root, gemini_provider="other"),
                    grok_model="grok-4.6", gemini_model="gemini-3.7-flash-high",
                    models_response_file=openai, codex_models_response_file=codex, timeout=1,
                )

    def test_loopback_hostname_and_address_are_equivalent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ids = ["grok-4.6", "gemini-3.7-flash-high"]
            openai, codex = self.files(root, ids, ids)
            config = self.config(root)
            config.write_text(config.read_text().replace("127.0.0.1", "localhost"))
            result = preflight.run_preflight(
                url="http://127.0.0.1:8317", config=config,
                grok_model=None, gemini_model="gemini-3.7-flash-high",
                models_response_file=openai, codex_models_response_file=codex, timeout=1,
            )
            self.assertEqual(result.provider_id, "cliproxyapi")

    def test_non_loopback_plain_http_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ids = ["grok-4.6", "gemini-3.7-flash-high"]
            openai, codex = self.files(root, ids, ids)
            with self.assertRaisesRegex(preflight.PreflightError, "plain HTTP"):
                preflight.run_preflight(
                    url="http://example.com:8317", config=self.config(root),
                    grok_model=None, gemini_model="gemini-3.7-flash-high",
                    models_response_file=openai, codex_models_response_file=codex, timeout=1,
                )
