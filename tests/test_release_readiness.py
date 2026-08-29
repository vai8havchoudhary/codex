from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "plugins/cliproxy-models/.codex-plugin/plugin.json"
MARKETPLACE_PATH = ROOT / ".agents/plugins/marketplace.json"


class ReleaseReadinessTests(unittest.TestCase):
    def test_release_documentation_is_present_and_complete(self) -> None:
        required = (
            "README.md",
            "AGENTS.md",
            "agent.md",
            "SETUP.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "CHANGELOG.md",
            "docs/RELEASING.md",
        )
        for relative in required:
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("[TODO", text, relative)
            self.assertNotIn("your-api-key", text.lower(), relative)

        setup = (ROOT / "SETUP.md").read_text(encoding="utf-8")
        self.assertIn("export CLIPROXY_URL=http://127.0.0.1:8317", setup)
        self.assertIn(
            'export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"',
            setup,
        )
        self.assertIn(
            "codex plugin marketplace add vai8havchoudhary/codex --ref main",
            setup,
        )
        self.assertIn("codex plugin add cliproxy-models@cliproxy", setup)
        self.assertIn("codex plugin marketplace upgrade cliproxy", setup)
        self.assertIn("codex plugin remove cliproxy-models@cliproxy", setup)

    def test_manifest_marketplace_and_changelog_versions_align(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        marketplace = json.loads(MARKETPLACE_PATH.read_text(encoding="utf-8"))
        version = manifest["version"]

        self.assertRegex(version, r"^[0-9]+\.[0-9]+\.[0-9]+$")
        self.assertEqual(manifest["name"], "cliproxy-models")
        self.assertEqual(marketplace["name"], "cliproxy")
        self.assertEqual(marketplace["plugins"][0]["name"], manifest["name"])

        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertRegex(changelog, rf"(?m)^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$")

    def test_agent_contract_names_security_and_validation_invariants(self) -> None:
        handbook = (ROOT / "agent.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for text in (handbook, agents):
            self.assertIn("cliproxy-models", text)
            self.assertIn("Grok 4.6", text)
            self.assertIn("Gemini 3.7 Flash", text)
            self.assertIn("CLIPROXY_API_KEY", text)
            self.assertIn("one", text.lower())
        self.assertIn("never echo its value", handbook)
        self.assertIn("atomic", handbook)
        self.assertIn("byte-idempotent", handbook)
        self.assertIn("docs/RELEASING.md", agents)

    def test_release_workflow_is_tag_guarded_and_packages_only_public_inputs(self) -> None:
        workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn('tags:', workflow)
        self.assertIn('actual_tag != expected_tag', workflow)
        self.assertIn('CHANGELOG.md has no dated section', workflow)
        self.assertIn('sha256sum', workflow)
        self.assertIn('gh release create', workflow)
        self.assertNotIn(".proxy-api-key", workflow)
        self.assertNotIn(".codex/config.toml", workflow)

    def test_validate_workflow_covers_supported_python_floor_and_release_runtime(self) -> None:
        workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
        self.assertIn('"3.11"', workflow)
        self.assertIn('"3.14"', workflow)
        self.assertTrue((ROOT / "tests/test_release_readiness.py").is_file())
        self.assertIn("compileall", workflow)


if __name__ == "__main__":
    unittest.main()
