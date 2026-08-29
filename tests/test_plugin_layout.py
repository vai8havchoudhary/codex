from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
EXPECTED = ("cliproxy-models", "hermes-moa")


class PluginLayoutTests(unittest.TestCase):
    def test_marketplace_and_manifest_contract(self) -> None:
        marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
        self.assertEqual(marketplace["name"], "cliproxy")
        self.assertEqual([entry["name"] for entry in marketplace["plugins"]], list(EXPECTED))
        for entry in marketplace["plugins"]:
            name = entry["name"]
            self.assertEqual(
                entry["source"],
                {"source": "local", "path": f"./plugins/{name}"},
            )
            self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
            self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")
            self.assertEqual(entry["policy"]["products"], ["CODEX"])

            plugin = PLUGINS / name
            manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text())
            self.assertEqual(manifest["name"], name)
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
            path = plugin / "commands" / f"{command}.md"
            self.assertTrue(path.is_file(), command)
            self.assertTrue(path.read_text().startswith("---\ndescription:"), command)

    def test_hermes_moa_components_are_complete(self) -> None:
        plugin = PLUGINS / "hermes-moa"
        skill = plugin / "skills/hermes-moa/SKILL.md"
        text = skill.read_text()
        self.assertTrue(text.startswith("---\nname: hermes-moa\n"))
        self.assertIn("cliproxy-grok-led", text)
        self.assertIn("cliproxy-gemini-led", text)
        self.assertIn("Never print", text)
        for script in ("catalog.py", "hermes_config.py", "plugin.py"):
            self.assertTrue((plugin / "scripts" / script).is_file(), script)
        for command in (
            "setup",
            "status",
            "use-grok-led",
            "use-gemini-led",
            "one-shot",
        ):
            path = plugin / "commands" / f"{command}.md"
            self.assertTrue(path.is_file(), command)
            self.assertTrue(path.read_text().startswith("---\ndescription:"), command)
        readme = (plugin / "README.md").read_text()
        self.assertIn("299c652a66bcc915a2a1e10cd2b648f196ec4bba", readme)
        self.assertIn("/moa", readme)

    def test_non_test_files_contain_no_key_fixture(self) -> None:
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.name.startswith("test_"):
                continue
            self.assertNotIn("not-a-real-secret-fixture", path.read_text(errors="ignore"))
        expected_export = (
            'export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"'
        )
        self.assertIn(expected_export, (ROOT / "README.md").read_text())
        self.assertIn(expected_export, (ROOT / "SETUP.md").read_text())


if __name__ == "__main__":
    unittest.main()
