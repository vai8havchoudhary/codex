from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
EXPECTED = ("cliproxy-models", "codex-moa")


class PluginLayoutTests(unittest.TestCase):
    def test_marketplace_contains_exact_native_plugins(self) -> None:
        marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
        self.assertEqual(marketplace["name"], "cliproxy")
        self.assertEqual([entry["name"] for entry in marketplace["plugins"]], list(EXPECTED))
        for entry in marketplace["plugins"]:
            name = entry["name"]
            self.assertEqual(entry["source"], {"source": "local", "path": f"./plugins/{name}"})
            self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
            self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")
            self.assertEqual(entry["policy"]["products"], ["CODEX"])
            self.assertEqual(entry["category"], "Developer Tools")

    def test_manifest_names_versions_and_assets(self) -> None:
        expected_versions = {"cliproxy-models": "1.0.0", "codex-moa": "2.0.0"}
        for name, version in expected_versions.items():
            plugin = PLUGINS / name
            manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text())
            self.assertEqual(manifest["name"], name)
            self.assertEqual(manifest["version"], version)
            self.assertEqual(manifest["skills"], "./skills/")
            self.assertLessEqual(len(manifest["interface"]["defaultPrompt"]), 3)
            self.assertTrue((plugin / manifest["interface"]["composerIcon"]).is_file())

    def test_cliproxy_models_components_are_complete(self) -> None:
        plugin = PLUGINS / "cliproxy-models"
        skill = plugin / "skills/cliproxy-models/SKILL.md"
        self.assertTrue(skill.read_text().startswith("---\nname: cliproxy-models\n"))
        for script in ("catalog.py", "config_edit.py", "install.py", "plugin.py"):
            self.assertTrue((plugin / "scripts" / script).is_file(), script)
        for command in ("setup", "status", "use-grok", "use-gemini"):
            self.assertTrue((plugin / "commands" / f"{command}.md").is_file(), command)

    def test_codex_moa_is_native_and_complete(self) -> None:
        plugin = PLUGINS / "codex-moa"
        manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text())
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")
        self.assertTrue((plugin / ".mcp.json").is_file())
        self.assertTrue((plugin / "mcp/server.py").is_file())
        self.assertTrue((plugin / "scripts/preflight.py").is_file())
        self.assertTrue((plugin / "scripts/checkpoint_schema.py").is_file())
        self.assertTrue((plugin / "skills/codex-moa/SKILL.md").is_file())
        for name in ("localizer", "critic", "writer", "recovery", "verifier"):
            self.assertTrue((plugin / "agents" / f"{name}.md").is_file(), name)
        for name in ("run", "grok-led", "gemini-led", "resume", "status", "review"):
            self.assertTrue((plugin / "commands" / f"{name}.md").is_file(), name)
        source = "\n".join(
            path.read_text(errors="ignore")
            for path in plugin.rglob("*")
            if path.is_file() and not path.name.startswith("test_")
        ).lower()
        self.assertIn("native codex", source)
        self.assertNotIn("hermes config", source)
        self.assertNotIn("hermes moa", source)

    def test_obsolete_bootstrap_and_hermes_paths_are_absent(self) -> None:
        self.assertFalse((ROOT / ".bootstrap").exists())
        self.assertFalse((ROOT / ".github/workflows/materialize-native-moa.yml").exists())
        self.assertFalse((PLUGINS / "hermes-moa").exists())
        self.assertFalse(list(ROOT.rglob("native-moa.b64.part-*")))

    def test_no_secret_fixture_outside_tests(self) -> None:
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.name.startswith("test_"):
                continue
            self.assertNotIn("not-a-real-secret-fixture", path.read_text(errors="ignore"), str(path))
        expected_export = 'export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"'
        self.assertIn(expected_export, (ROOT / "README.md").read_text())
        self.assertIn(expected_export, (ROOT / "SETUP.md").read_text())


if __name__ == "__main__":
    unittest.main()
