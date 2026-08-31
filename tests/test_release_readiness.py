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
    def test_model_setup_and_status_commands_cover_named_install_contract(self) -> None:
        commands = ROOT / "plugins/cliproxy-models/commands"
        for name in ("setup", "status"):
            text = (commands / f"{name}.md").read_text()
            for item in ("gpt-5.6-luna", "luna-grok", "grok-gemini", "--gemini-model gemini-3.7-flash-high"):
                self.assertIn(item, text, name)
        self.assertIn("`grok`, `gemini`, or `luna`", (commands / "setup.md").read_text())
        self.assertIn("does not prove native delegation", (commands / "status.md").read_text())

    def test_security_inventory_and_hardening_cover_every_managed_document(self) -> None:
        security = (ROOT / "SECURITY.md").read_text()
        expected = {
            "config.toml", "cliproxy-grok-4-6.config.toml",
            "cliproxy-gemini-3-7-flash.config.toml", "cliproxy-luna.config.toml",
            "luna-grok.config.toml", "grok-gemini.config.toml",
            "cliproxy-council-models.json",
        }
        inventory = set(re.findall(r"(?m)^~/.codex/([A-Za-z0-9.-]+)$", security))
        hardening = set(re.findall(r'(?m)^chmod 600 "\$HOME/\.codex/([A-Za-z0-9.-]+)"$', security))
        self.assertEqual(inventory, expected)
        self.assertEqual(hardening, expected)
        for concept in ("_codex_cliproxy_models", "model_catalog_json", "developer_instructions",
                        "symlink", "concurrent-change", "rollback", "post-validation"):
            self.assertIn(concept, security)
        for model in ("gpt-5.6-luna", "grok-4.6", "gemini-3.7-flash-high"):
            self.assertIn(model, security)
        self.assertIn("Gemini-led new runs are unsupported", security)
        self.assertIn("Leader obligations apply only to the root", security)

    def test_public_security_and_privacy_explain_stored_metadata_and_witness_limits(self) -> None:
        for name in ("SECURITY.md", "PRIVACY.md"):
            with self.subTest(document=name):
                text = (ROOT / name).read_text()
                for concept in ("cliproxy-council-models.json", "model_catalog_json",
                                "developer_instructions", "luna-grok", "grok-gemini",
                                "full live Codex descriptors", "capabilities", "model instructions",
                                "agent IDs", "model IDs", "verdicts", "transcript references",
                                "reviewed revisions", "not authenticated attestations",
                                "payload integrity", "Schema-2", "Schema-1", "read-only",
                                "CLIPROXY_API_KEY", "CODEX_HOME", "0600", "0700"):
                    self.assertIn(concept, text)
                self.assertIn("No plugin reads or enumerates proxy account files", text)
                self.assertIn("not a general-purpose", text)
        privacy = (ROOT / "PRIVACY.md").read_text()
        self.assertIn("does not synthesize capabilities or add credentials", privacy)
        self.assertIn("Server-supplied descriptors are not redacted", privacy)
        self.assertIn("not upload checkpoints or model-catalog snapshots as telemetry", privacy)
        self.assertIn("user-directed sharing may send task context", privacy)

    def test_release_marketplace_manifests_and_authority_versions_align(self) -> None:
        release = json.loads(RELEASE.read_text())
        marketplace = json.loads(MARKETPLACE.read_text())
        authority = json.loads(AUTHORITY.read_text())
        self.assertEqual(release["name"], "cliproxy-plugins")
        self.assertEqual(release["version"], "2.0.0")
        self.assertEqual(release["plugins"], {"cliproxy-models": "1.1.0", "codex-moa": "2.0.0"})
        names = {entry["name"] for entry in marketplace["plugins"]}
        self.assertEqual(set(release["plugins"]), names)
        for name, expected_version in release["plugins"].items():
            manifest = json.loads((ROOT / f"plugins/{name}/.codex-plugin/plugin.json").read_text())
            self.assertEqual(manifest["name"], name)
            self.assertEqual(manifest["version"], expected_version)
        self.assertEqual(authority["schema"], 1)
        self.assertEqual(authority["marketplace"], marketplace["name"])
        self.assertEqual(authority["release"], {"name": release["name"], "version": release["version"]})
        self.assertEqual(authority["consumer"], {"name": "codex-moa", "version": "2.0.0"})
        self.assertEqual(authority["authority"]["name"], "cliproxy-models")
        self.assertEqual(authority["authority"]["version"], "1.1.0")
        changelog = (ROOT / "CHANGELOG.md").read_text()
        self.assertRegex(changelog, r"(?m)^## \[2\.0\.0\] - 2026-08-30$")
        self.assertIn("cliproxy-models` 1.1.0", changelog)

    def test_docs_cover_modern_profiles_native_boundary_and_live_evidence(self) -> None:
        for relative in ("README.md", "SETUP.md", "AGENTS.md", "agent.md"):
            text = (ROOT / relative).read_text()
            for phrase in (
                "cliproxy-models",
                "codex-moa",
                "grok-4.6",
                "gemini-3.7-flash-high",
                "gemini-3.7-flash-advisor",
                "CLIPROXY_API_KEY",
                "cliproxy-grok-4-6.config.toml",
                "cliproxy-gemini-3-7-flash.config.toml",
            ):
                self.assertIn(phrase, text, relative)
        setup = (ROOT / "SETUP.md").read_text()
        self.assertIn("seven-file", setup)
        self.assertIn("[profiles.*]", setup)
        self.assertIn("--profile cliproxy-grok-4-6", setup)
        self.assertIn("transaction", setup.lower())
        evidence = (ROOT / "docs/VPS2_GATE_2026-08-30.md").read_text()
        for phrase in (
            "74a2c0940f8bc411e9fa1820faed5aec121a7829",
            "e50ec6861d2a6daa6b9090c82ce214c44ee3e5ce",
            "38354612ea434380a8bbb7b16e149e58",
            "01a05354-fb49-76b2-8bad-88e9e997d026",
            "46c3521bbdc24394ba250a3c055bc5fc",
            "d7c5e3595baf49109e4752d148847346",
            "f853cc0b429a4dd38cf84d7b8f12f2fc",
            "21443c8283a640d2b176dcfdeb11a427",
            "does **not** waive",
        ):
            self.assertIn(phrase, evidence)

    def test_profile_transaction_and_preflight_contract_are_fail_closed(self) -> None:
        writer = "\n".join(
            (ROOT / "plugins/cliproxy-models/scripts" / name).read_text()
            for name in ("config_edit.py", "toml_edit.py", "profile_documents.py", "config_transaction.py")
        )
        installer = (ROOT / "plugins/cliproxy-models/scripts/install.py").read_text()
        preflight = (ROOT / "plugins/codex-moa/scripts/preflight.py").read_text()
        for phrase in (
            "transactional_write",
            "_assert_unchanged",
            "refusing symlink",
            "post-write validation",
            "configuration transaction failed and was rolled back",
            "REQUIRED_MODE = 0o600",
        ):
            self.assertIn(phrase, writer)
        self.assertIn("render_documents", installer)
        self.assertIn("_profile_overlay(config, GROK_PROFILE)", preflight)
        self.assertIn("_profile_overlay(config, GEMINI_PROFILE)", preflight)
        self.assertIn("legacy `[profiles.*]`", preflight)
        self.assertNotIn("def _profile(parsed", preflight)

    def test_release_workflow_is_guarded_and_packages_tracked_source(self) -> None:
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        for phrase in (
            '"release/v*"',
            'ref_type == "tag"',
            'ref_type == "branch"',
            "git rev-parse origin/main",
            'git tag -a "$TAG"',
            "release.json",
            "plugins/codex-moa/authority.json",
            "plugins/*/authority.json",
            "plugins \\",
            "sha256sum",
        ):
            self.assertIn(phrase, workflow)
        for forbidden in (".proxy-api-key", ".codex/config.toml", "native-moa.b64"):
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

    def test_releasing_guide_requires_fresh_profile_gate(self) -> None:
        guide = (ROOT / "docs/RELEASING.md").read_text()
        self.assertIn("`release.json` is authoritative", guide)
        self.assertIn('"cliproxy-models": "1.1.0"', guide)
        self.assertIn("Do not publish before the fresh exact-main gate", guide)
        self.assertIn("codex exec --profile", guide)
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


if __name__ == "__main__":
    unittest.main()
