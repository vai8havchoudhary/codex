from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".agents/plugins/marketplace.json"
RELEASE = ROOT / "release.json"
AUTHORITY = ROOT / "plugins/codex-moa/authority.json"


class ReleaseReadinessTests(unittest.TestCase):
    def test_release_marketplace_manifests_and_authority_versions_align(self) -> None:
        release = json.loads(RELEASE.read_text())
        marketplace = json.loads(MARKETPLACE.read_text())
        authority = json.loads(AUTHORITY.read_text())
        self.assertEqual(release["name"], "cliproxy-plugins")
        self.assertEqual(release["version"], "2.0.0")
        names = {entry["name"] for entry in marketplace["plugins"]}
        self.assertEqual(set(release["plugins"]), names)
        for name, expected_version in release["plugins"].items():
            manifest = json.loads(
                (ROOT / f"plugins/{name}/.codex-plugin/plugin.json").read_text()
            )
            self.assertEqual(manifest["name"], name)
            self.assertEqual(manifest["version"], expected_version)

        self.assertEqual(authority["schema"], 1)
        self.assertEqual(authority["marketplace"], marketplace["name"])
        self.assertEqual(authority["release"]["name"], release["name"])
        self.assertEqual(authority["release"]["version"], release["version"])
        self.assertEqual(
            release["plugins"][authority["consumer"]["name"]],
            authority["consumer"]["version"],
        )
        self.assertEqual(
            release["plugins"][authority["authority"]["name"]],
            authority["authority"]["version"],
        )

        changelog = (ROOT / "CHANGELOG.md").read_text()
        self.assertRegex(changelog, r"(?m)^## \[2\.0\.0\] - 2026-08-30$")

    def test_docs_cover_native_boundary_live_ambiguity_and_cache_contract(self) -> None:
        for relative in (
            "README.md",
            "SETUP.md",
            "AGENTS.md",
            "agent.md",
            "CONTRIBUTING.md",
        ):
            text = (ROOT / relative).read_text()
            for phrase in (
                "cliproxy-models",
                "codex-moa",
                "grok-4.6",
                "gemini-3.7-flash-high",
                "gemini-3.7-flash-advisor",
                "CLIPROXY_API_KEY",
            ):
                self.assertIn(phrase, text, relative)
        setup = (ROOT / "SETUP.md").read_text()
        self.assertIn("Automatic setup must refuse", setup)
        self.assertIn("--gemini-model gemini-3.7-flash-high", setup)
        self.assertIn("versioned Codex cache", setup)
        self.assertIn("authority.json", setup)
        handbook = (ROOT / "agent.md").read_text()
        self.assertIn("no external model loop", handbook.lower())
        self.assertIn("two coherent repair rounds", handbook)
        self.assertIn("authority.json", handbook)

    def test_release_workflow_is_guarded_and_packages_tracked_source(self) -> None:
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
            "plugins/codex-moa",
            "obsolete release paths remain",
            "plugins/codex-moa/authority.json",
            "plugins/*/authority.json",
        ):
            self.assertIn(phrase, workflow)
        for forbidden in (
            ".proxy-api-key",
            ".codex/config.toml",
            ".hermes/config.yaml",
            "native-moa.b64",
        ):
            self.assertNotIn(forbidden, workflow)

    def test_validate_workflow_discovers_all_tests_and_mcp(self) -> None:
        workflow = (ROOT / ".github/workflows/validate.yml").read_text()
        self.assertIn('"3.11"', workflow)
        self.assertIn('"3.14"', workflow)
        self.assertIn("plugins/*/scripts plugins/*/tests", workflow)
        self.assertIn("plugins/*/authority.json", workflow)
        self.assertIn("plugins/*/.mcp.json", workflow)
        self.assertIn("test ! -e .bootstrap", workflow)
        self.assertIn("test ! -e plugins/hermes-moa", workflow)

    def test_release_guide_forbids_premature_publication_and_bootstrap(self) -> None:
        guide = (ROOT / "docs/RELEASING.md").read_text()
        self.assertIn("`release.json` is authoritative", guide)
        self.assertIn("Do not publish before the exact-main live gate", guide)
        self.assertIn("Bootstrap archives", guide)
        self.assertIn("Do not move a published tag", guide)
        self.assertIn("release/v2.0.0", guide)

    def test_mcp_config_does_not_receive_proxy_authority(self) -> None:
        mcp = json.loads((ROOT / "plugins/codex-moa/.mcp.json").read_text())
        server = mcp["mcpServers"]["codex-moa-checkpoints"]
        self.assertEqual(server["env_vars"], ["CODEX_HOME"])
        encoded = json.dumps(mcp)
        self.assertNotIn("CLIPROXY_API_KEY", encoded)
        self.assertNotIn("CLIPROXY_URL", encoded)
        self.assertNotIn("account", encoded.lower())

    def test_research_file_maps_primary_sources_to_policy(self) -> None:
        text = (
            ROOT / "plugins/codex-moa/references/long-horizon-research.md"
        ).read_text()
        for identifier in (
            "2405.15793",
            "2407.01489",
            "2309.12499",
            "2406.11638",
            "2406.04692",
            "2303.11366",
        ):
            self.assertIn(identifier, text)
        self.assertIn("one acting trajectory", text)


if __name__ == "__main__":
    unittest.main()
