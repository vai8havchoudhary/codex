from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "cliproxy-models"


class PluginLayoutTests(unittest.TestCase):
    def test_marketplace_and_manifest_contract(self) -> None:
        marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
        self.assertEqual(marketplace["name"], "cliproxy")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "cliproxy-models")
        self.assertEqual(entry["source"], {"source": "local", "path": "./plugins/cliproxy-models"})
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")
        self.assertEqual(entry["policy"]["products"], ["CODEX"])

        manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
        self.assertEqual(manifest["name"], "cliproxy-models")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertLessEqual(len(manifest["interface"]["defaultPrompt"]), 3)
        self.assertTrue((PLUGIN / manifest["interface"]["composerIcon"]).is_file())

    def test_skill_commands_and_scripts_are_complete(self) -> None:
        skill = PLUGIN / "skills/cliproxy-models/SKILL.md"
        text = skill.read_text()
        self.assertTrue(text.startswith("---\nname: cliproxy-models\n"))
        self.assertIn("Never print", text)
        for script in ("catalog.py", "config_edit.py", "install.py", "plugin.py"):
            self.assertTrue((PLUGIN / "scripts" / script).is_file(), script)
        for command in ("setup", "status", "use-grok", "use-gemini"):
            path = PLUGIN / "commands" / f"{command}.md"
            self.assertTrue(path.is_file(), command)
            self.assertTrue(path.read_text().startswith("---\ndescription:"), command)

    def test_non_test_files_contain_no_key_fixture(self) -> None:
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.name.startswith("test_"):
                continue
            self.assertNotIn("not-a-real-secret-fixture", path.read_text(errors="ignore"))
        self.assertIn(
            'export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"',
            (ROOT / "README.md").read_text(),
        )


if __name__ == "__main__":
    unittest.main()
