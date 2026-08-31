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
SPEC = importlib.util.spec_from_file_location("cliproxy_install", MODULE_PATH)
assert SPEC and SPEC.loader
install = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = install
SPEC.loader.exec_module(install)
config_edit = sys.modules["config_edit"]
config_transaction = sys.modules["config_transaction"]


def catalogs(openai: list[str], codex: list[str] | None = None):
    return install.Catalogs(tuple(openai) + ("gpt-5.6-luna",), tuple(codex or openai) + ("gpt-5.6-luna",))


class CatalogTests(unittest.TestCase):
    def test_extracts_openai_and_codex_shapes(self):
        self.assertEqual(
            install.extract_openai_ids({"data": [{"id": "grok-4.6"}]}),
            ("grok-4.6",),
        )
        self.assertEqual(
            install.extract_codex_slugs(
                {"models": [{"slug": "gemini-3.7-flash"}]}
            ),
            ("gemini-3.7-flash",),
        )

    def test_resolves_namespaced_exact_aliases(self):
        result = install.resolve_models(
            catalogs(["xai/grok-4.6", "google/gemini-3.7-flash"])
        )
        self.assertEqual(
            result,
            install.Models("xai/grok-4.6", "google/gemini-3.7-flash"),
        )

    def test_rejects_nearby_versions_and_markerless_gemini(self):
        for values in (
            ["grok-4.60", "gemini-3.7-flash"],
            ["grok-4.6.1", "gemini-3.7-flash"],
            ["grok-4.6", "gemini-3.70-flash"],
            ["grok-4.6", "gemini-3.7"],
        ):
            with self.subTest(values=values), self.assertRaises(install.InstallError):
                install.resolve_models(catalogs(values))

    def test_requires_alias_in_both_catalogs(self):
        with self.assertRaisesRegex(install.InstallError, "both catalogs"):
            install.resolve_models(
                catalogs(
                    ["grok-4.6", "gemini-3.7-flash"],
                    ["grok-4.6"],
                )
            )

    def test_ambiguity_requires_explicit_alias(self):
        values = ["grok-4.6", "xai/grok-4.6", "gemini-3.7-flash"]
        with self.assertRaisesRegex(install.InstallError, "multiple possible aliases"):
            install.resolve_models(catalogs(values))
        result = install.resolve_models(catalogs(values), grok="xai/grok-4.6")
        self.assertEqual(result.grok, "xai/grok-4.6")

    def test_vps2_gemini_high_and_advisor_are_ambiguous_until_explicit(self):
        values = [
            "grok-4.6",
            "gemini-3.7-flash-high",
            "gemini-3.7-flash-advisor",
        ]
        with self.assertRaisesRegex(install.InstallError, "multiple possible aliases"):
            install.resolve_models(catalogs(values))
        result = install.resolve_models(
            catalogs(values),
            gemini="gemini-3.7-flash-high",
        )
        self.assertEqual(result.grok, "grok-4.6")
        self.assertEqual(result.gemini, "gemini-3.7-flash-high")

    def test_explicit_vps2_alias_must_exist_in_both_catalogs(self):
        with self.assertRaisesRegex(install.InstallError, "both CLIProxyAPI catalogs"):
            install.resolve_models(
                catalogs(
                    ["grok-4.6", "gemini-3.7-flash-high"],
                    ["grok-4.6", "gemini-3.7-flash-advisor"],
                ),
                gemini="gemini-3.7-flash-high",
            )

    def test_offline_requires_both_catalog_shapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "models.json"
            path.write_text(json.dumps({"data": [{"id": "grok-4.6"}]}))
            with self.assertRaisesRegex(install.InstallError, "also requires"):
                install.read_catalogs(
                    "http://127.0.0.1:8317/v1",
                    None,
                    path,
                    None,
                    1,
                )


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.provider = install.Provider(
            "cliproxyapi",
            "CLIProxyAPI",
            "http://127.0.0.1:8317/v1",
            "CLIPROXY_API_KEY",
            True,
        )
        self.models = install.Models("grok-4.6", "gemini-3.7-flash-high")

    def render(self, base: str = "", grok: str = "", gemini: str = ""):
        return config_edit.render_documents(
            base_original=base,
            grok_original=grok,
            gemini_original=gemini,
            catalog_path=Path("/tmp/fixture-council-models.json"),
            provider=self.provider,
            models=self.models,
            activate_provider=True,
            default_model=self.models.grok,
        )

    def test_reuses_one_existing_provider_and_preserves_env_key(self):
        parsed = tomllib.loads(
            '''[model_providers.proxy]
name = "CLIProxyAPI"
base_url = "http://localhost:8317/v1"
env_key = "EXISTING_TOKEN"
'''
        )
        provider = install.choose_provider(
            parsed,
            "cliproxyapi",
            "http://127.0.0.1:8317/v1",
            None,
        )
        self.assertEqual(provider.provider_id, "proxy")
        self.assertEqual(provider.env_key, "EXISTING_TOKEN")
        self.assertFalse(provider.is_new)

    def test_refuses_unrelated_provider_collision(self):
        parsed = tomllib.loads(
            '''[model_providers.cliproxyapi]
name = "Other"
base_url = "https://example.com/v1"
'''
        )
        with self.assertRaisesRegex(install.InstallError, "unrelated"):
            install.choose_provider(
                parsed,
                "cliproxyapi",
                "http://127.0.0.1:8317/v1",
                None,
            )

    def test_fresh_install_uses_modern_profile_files(self):
        docs = self.render()
        base = tomllib.loads(docs.base)
        grok = tomllib.loads(docs.grok)
        gemini = tomllib.loads(docs.gemini)
        self.assertNotIn("profiles", base)
        self.assertNotIn("profile", base)
        self.assertEqual(base["model"], "grok-4.6")
        self.assertEqual(base["model_provider"], "cliproxyapi")
        self.assertEqual(grok["model"], "grok-4.6")
        self.assertEqual(grok["model_provider"], "cliproxyapi")
        self.assertEqual(gemini["model"], "gemini-3.7-flash-high")
        self.assertEqual(gemini["model_provider"], "cliproxyapi")
        self.assertNotIn("profiles", grok)
        self.assertNotIn("profiles", gemini)

    def test_migrates_managed_legacy_tables_and_selector(self):
        legacy = f'''profile = "{install.GROK_PROFILE}" # old managed selector
model = "grok-4.6" # keep

{install.BEGIN}
[model_providers.cliproxyapi]
name = "CLIProxyAPI"
base_url = "http://127.0.0.1:8317/v1"
wire_api = "responses"
requires_openai_auth = false
env_key = "CLIPROXY_API_KEY"

[profiles.{install.GROK_PROFILE}]
model = "grok-4.6"
model_provider = "cliproxyapi"

[profiles.{install.GEMINI_PROFILE}]
model = "gemini-3.7-flash-high"
model_provider = "cliproxyapi"
{install.END}
'''
        docs = self.render(base=legacy)
        parsed = tomllib.loads(docs.base)
        self.assertNotIn("profile", parsed)
        self.assertNotIn("profiles", parsed)
        self.assertEqual(parsed["model"], "grok-4.6")
        self.assertIn("# keep", docs.base)
        self.assertEqual(docs.base.count(install.BEGIN), 1)

    def test_preserves_unrelated_base_and_profile_toml_comments(self):
        base = 'model = "grok-4.6" # keep base\n\n[[hooks]]\ncommand = "echo ok"\n'
        grok = 'approval_policy = "on-request" # keep profile\n\n[tools]\nweb = true\n'
        docs = self.render(base=base, grok=grok)
        self.assertIn("# keep base", docs.base)
        self.assertIn("# keep profile", docs.grok)
        self.assertEqual(tomllib.loads(docs.base)["hooks"][0]["command"], "echo ok")
        self.assertTrue(tomllib.loads(docs.grok)["tools"]["web"])

    def test_profile_unmanaged_model_collision_is_refused(self):
        with self.assertRaisesRegex(install.InstallError, "unmanaged model"):
            self.render(grok='model = "user-owned"\n')

    def test_unmanaged_legacy_base_profile_is_refused(self):
        with self.assertRaisesRegex(install.InstallError, "unmanaged legacy"):
            self.render(base='[profiles.unrelated]\nmodel = "gpt"\n')

    def test_unmanaged_foreign_selector_is_refused(self):
        with self.assertRaisesRegex(install.InstallError, "unmanaged legacy"):
            self.render(base='profile = "foreign"\n')

    def test_malformed_managed_profile_block_is_refused(self):
        with self.assertRaisesRegex(install.InstallError, "malformed"):
            self.render(grok=f"{config_edit.PROFILE_BEGIN}\nmodel = \"grok-4.6\"\n")

    def test_render_is_byte_idempotent(self):
        first = self.render()
        second = config_edit.render_documents(
            base_original=first.base,
            grok_original=first.grok,
            gemini_original=first.gemini,
            catalog_path=Path("/tmp/fixture-council-models.json"),
            provider=install.Provider(
                self.provider.provider_id,
                self.provider.name,
                self.provider.base_url,
                self.provider.env_key,
                False,
            ),
            models=self.models,
            activate_provider=True,
            default_model=None,
        )
        self.assertEqual(first, second)

    def test_profiles_only_leaves_active_provider(self):
        docs = config_edit.render_documents(
            base_original='model = "gpt-5.6"\nmodel_provider = "openai"\n',
            grok_original="",
            gemini_original="",
            catalog_path=Path("/tmp/fixture-council-models.json"),
            provider=self.provider,
            models=self.models,
            activate_provider=False,
            default_model=None,
        )
        self.assertEqual(tomllib.loads(docs.base)["model_provider"], "openai")


if __name__ == "__main__":
    unittest.main()
