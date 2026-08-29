from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".agents/plugins/marketplace.json"
RELEASE = ROOT / "release.json"


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
        for phrase in (
            "export CLIPROXY_URL=http://127.0.0.1:8317",
            'export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"',
            "codex plugin marketplace add vai8havchoudhary/codex --ref main",
            "codex plugin add cliproxy-models@cliproxy",
            "codex plugin add hermes-moa@cliproxy",
            "codex plugin marketplace upgrade cliproxy",
            "codex plugin remove hermes-moa@cliproxy",
            "/model cliproxy-grok-led --provider moa",
            "/moa <one-shot prompt",
        ):
            self.assertIn(phrase, setup)

    def test_release_marketplace_and_manifest_versions_align(self) -> None:
        release = json.loads(RELEASE.read_text())
        marketplace = json.loads(MARKETPLACE.read_text())
        version = release["version"]
        self.assertRegex(version, r"^[0-9]+\.[0-9]+\.[0-9]+$")
        names = {entry["name"] for entry in marketplace["plugins"]}
        self.assertEqual(set(release["plugins"]), names)
        for name, expected_version in release["plugins"].items():
            manifest = json.loads(
                (ROOT / f"plugins/{name}/.codex-plugin/plugin.json").read_text()
            )
            self.assertEqual(manifest["name"], name)
            self.assertEqual(manifest["version"], expected_version)

        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertRegex(
            changelog,
            rf"(?m)^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$",
        )

    def test_agent_contract_covers_both_plugins_and_security_invariants(self) -> None:
        handbook = (ROOT / "agent.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for text in (handbook, agents):
            for phrase in (
                "cliproxy-models",
                "hermes-moa",
                "Grok 4.6",
                "Gemini 3.7 Flash",
                "CLIPROXY_API_KEY",
                "cliproxy-grok-led",
                "cliproxy-gemini-led",
                "release.json",
            ):
                self.assertIn(phrase, text)
        self.assertIn("exact original bytes", handbook)
        self.assertIn("docs/RELEASING.md", agents)

    def test_release_workflow_is_guarded_and_packages_all_plugins(self) -> None:
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        for phrase in (
            '"release/v*"',
            'ref_type == "tag"',
            'ref_type == "branch"',
            'expected_branch = f"release/{expected_tag}"',
            "git rev-parse origin/main",
            'git tag -a "$TAG"',
            'git push origin "refs/tags/$TAG"',
            "release.json",
            "set(mapped) != entries",
            "plugins \\",
            "sha256sum",
            'gh release create "$TAG"',
        ):
            self.assertIn(phrase, workflow)
        self.assertNotIn(".proxy-api-key", workflow)
        self.assertNotIn(".codex/config.toml", workflow)
        self.assertNotIn(".hermes/config.yaml", workflow)

    def test_validate_workflow_discovers_every_plugin_suite(self) -> None:
        workflow = (ROOT / ".github/workflows/validate.yml").read_text()
        self.assertIn('"3.11"', workflow)
        self.assertIn('"3.14"', workflow)
        self.assertIn("plugins/*/scripts", workflow)
        self.assertIn("plugins/*/.codex-plugin/plugin.json", workflow)
        self.assertIn("compileall -q plugins tests", workflow)

    def test_releasing_guide_documents_marketplace_authority(self) -> None:
        guide = (ROOT / "docs/RELEASING.md").read_text()
        self.assertIn("`release.json` is authoritative", guide)
        self.assertIn("Publication path A: annotated tag", guide)
        self.assertIn("Publication path B: guarded promotion branch", guide)
        self.assertIn("requires the promotion branch commit to equal current `main`", guide)
        self.assertIn("Do not move a published tag", guide)


if __name__ == "__main__":
    unittest.main()
