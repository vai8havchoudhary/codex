from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SOURCE_AUTHORITY_ROOT = PLUGIN_ROOT.parent / "cliproxy-models"
MODULE_PATH = PLUGIN_ROOT / "scripts" / "preflight.py"
SPEC = importlib.util.spec_from_file_location("codex_moa_preflight_test", MODULE_PATH)
assert SPEC and SPEC.loader
preflight = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = preflight
SPEC.loader.exec_module(preflight)


class PreflightTests(unittest.TestCase):
    def _files(
        self,
        root: Path,
        openai_ids: list[str],
        codex_ids: list[str],
    ) -> tuple[Path, Path]:
        root.mkdir(parents=True, exist_ok=True)
        openai = root / "models.json"
        codex = root / "codex-models.json"
        openai.write_text(json.dumps({"data": [{"id": value} for value in openai_ids]}))
        codex.write_text(json.dumps({"models": [{"slug": value} for value in codex_ids]}))
        return openai, codex

    def _config(self, root: Path, gemini: str = "gemini-3.7-flash-high") -> Path:
        root.mkdir(parents=True, exist_ok=True)
        path = root / "config.toml"
        path.write_text(
            f'''[model_providers.cliproxyapi]
name = "CLIProxyAPI"
base_url = "http://127.0.0.1:8317/v1"
env_key = "CLIPROXY_API_KEY"
wire_api = "responses"
requires_openai_auth = false

[profiles.cliproxy-grok-4-6]
model = "grok-4.6"
model_provider = "cliproxyapi"

[profiles.cliproxy-gemini-3-7-flash]
model = "{gemini}"
model_provider = "cliproxyapi"
'''
        )
        return path

    def _copy_plugin(self, source: Path, destination: Path, version: str | None = None) -> None:
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        if version is not None:
            manifest_path = destination / ".codex-plugin/plugin.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["version"] = version
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    def _installed_cache(
        self,
        root: Path,
        authority_versions: tuple[str, ...],
    ) -> tuple[Path, Path]:
        marketplace = root / "cache" / "cliproxy"
        consumer = marketplace / "codex-moa" / "2.0.0"
        self._copy_plugin(PLUGIN_ROOT, consumer)
        versions_root = marketplace / "cliproxy-models"
        for version in authority_versions:
            self._copy_plugin(
                SOURCE_AUTHORITY_ROOT,
                versions_root / version,
                version=version,
            )
        return consumer, versions_root

    def _run_success(self, root: Path, plugin_root: Path = PLUGIN_ROOT):
        ids = ["grok-4.6", "gemini-3.7-flash-high"]
        openai, codex = self._files(root, ids, ids)
        return preflight.run_preflight(
            url="http://127.0.0.1:8317",
            config=self._config(root),
            grok_model="grok-4.6",
            gemini_model="gemini-3.7-flash-high",
            models_response_file=openai,
            codex_models_response_file=codex,
            timeout=1,
            plugin_root=plugin_root,
        )

    def test_source_checkout_uses_release_bound_sibling_authority(self) -> None:
        expected = (SOURCE_AUTHORITY_ROOT / "scripts").resolve()
        self.assertEqual(preflight.locate_authority_scripts(PLUGIN_ROOT), expected)
        catalog, adapter = preflight.load_authority(PLUGIN_ROOT)
        self.assertEqual(Path(catalog.__file__).resolve(), expected / "catalog.py")
        self.assertEqual(Path(adapter.__file__).resolve(), expected / "plugin.py")

    def test_versioned_codex_cache_loads_pinned_authority_and_preflight_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            consumer, versions_root = self._installed_cache(root, ("1.0.0",))
            expected = (versions_root / "1.0.0" / "scripts").resolve()
            catalog, adapter = preflight.load_authority(consumer)
            self.assertEqual(Path(catalog.__file__).resolve(), expected / "catalog.py")
            self.assertEqual(Path(adapter.__file__).resolve(), expected / "plugin.py")
            result = self._run_success(root / "fixtures", consumer)
            self.assertEqual(result.provider_id, "cliproxyapi")
            self.assertEqual(result.grok_model, "grok-4.6")
            self.assertEqual(result.gemini_model, "gemini-3.7-flash-high")

    def test_pinned_cache_version_wins_without_guessing_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            consumer, versions_root = self._installed_cache(
                Path(tmp),
                ("1.0.0", "1.1.0"),
            )
            self.assertEqual(
                preflight.locate_authority_scripts(consumer),
                (versions_root / "1.0.0" / "scripts").resolve(),
            )

    def test_missing_cache_authority_has_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            consumer, _ = self._installed_cache(Path(tmp), ())
            with self.assertRaisesRegex(
                preflight.PreflightError,
                r"requires cliproxy-models 1\.0\.0.*codex plugin add cliproxy-models@cliproxy",
            ):
                preflight.load_authority(consumer)

    def test_incompatible_cache_versions_are_listed_and_not_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            consumer, _ = self._installed_cache(Path(tmp), ("0.9.0", "1.1.0"))
            with self.assertRaises(preflight.PreflightError) as raised:
                preflight.load_authority(consumer)
            message = str(raised.exception)
            self.assertIn("Installed versions: 0.9.0, 1.1.0.", message)
            self.assertIn("Refusing to choose another version.", message)
            self.assertIn("cliproxy-models 1.0.0", message)

    def test_exact_cache_directory_with_wrong_manifest_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            consumer, versions_root = self._installed_cache(Path(tmp), ("1.0.0",))
            manifest_path = versions_root / "1.0.0/.codex-plugin/plugin.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["version"] = "1.0.1"
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(
                preflight.PreflightError,
                r"expected 'cliproxy-models' '1\.0\.0'",
            ):
                preflight.load_authority(consumer)

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
