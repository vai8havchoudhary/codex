from __future__ import annotations

import json
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]


class LayoutTests(unittest.TestCase):
    def test_manifest_mcp_skill_agents_commands_and_authority_contract(self) -> None:
        manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
        self.assertEqual(manifest["name"], "codex-moa")
        self.assertEqual(manifest["version"], "2.0.0")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")
        self.assertTrue((PLUGIN / manifest["interface"]["composerIcon"]).is_file())

        authority = json.loads((PLUGIN / "authority.json").read_text())
        self.assertEqual(authority["schema"], 1)
        self.assertEqual(authority["marketplace"], "cliproxy")
        self.assertEqual(authority["release"], {"name": "cliproxy-plugins", "version": "2.0.0"})
        self.assertEqual(authority["consumer"], {"name": "codex-moa", "version": "2.0.0"})
        self.assertEqual(authority["authority"]["name"], "cliproxy-models")
        self.assertEqual(authority["authority"]["version"], "1.1.0")
        self.assertEqual(authority["authority"]["scripts"], ["catalog.py", "plugin.py"])
        self.assertNotIn("CLIPROXY_API_KEY", json.dumps(authority))

        mcp = json.loads((PLUGIN / ".mcp.json").read_text())
        definition = mcp["mcpServers"]["codex-moa-checkpoints"]
        self.assertEqual(definition["command"], "python3")
        self.assertEqual(definition["env_vars"], ["CODEX_HOME"])
        self.assertNotIn("CLIPROXY_API_KEY", json.dumps(mcp))

        skill = (PLUGIN / "skills/codex-moa/SKILL.md").read_text()
        for phrase in (
            "name: codex-moa",
            "spawn_agent",
            "single-writer",
            "checkpoint_put",
            "gemini-3.7-flash-high",
            "gemini-3.7-flash-advisor",
            "Do not choose",
            "Never claim completion",
        ):
            self.assertIn(phrase, skill)
        self.assertNotIn("hermes config", skill.lower())

        for name in ("localizer", "critic", "writer", "recovery", "verifier"):
            self.assertTrue((PLUGIN / "agents" / f"{name}.md").is_file())
        for name in ("run", "grok-led", "gemini-led", "resume", "status", "review"):
            command = PLUGIN / "commands" / f"{name}.md"
            self.assertTrue(command.is_file())
            self.assertTrue(command.read_text().startswith("---\ndescription:"))

    def test_research_mapping_is_primary_source_grounded(self) -> None:
        research = (PLUGIN / "references/long-horizon-research.md").read_text()
        for arxiv_id in (
            "2405.15793",
            "2407.01489",
            "2309.12499",
            "2406.11638",
            "2406.04692",
            "2303.11366",
        ):
            self.assertIn(arxiv_id, research)
        self.assertIn("one acting trajectory", research)
        self.assertIn("does not implement a competing scheduler", research)


if __name__ == "__main__":
    unittest.main()
