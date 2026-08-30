from __future__ import annotations

import json
import tempfile
from pathlib import Path

from support import PLUGIN_ROOT, SOURCE_AUTHORITY_ROOT, PreflightTestCase, preflight


class AuthorityLocationTests(PreflightTestCase):
    def test_source_checkout_uses_release_bound_sibling_authority(self) -> None:
        expected = (SOURCE_AUTHORITY_ROOT / "scripts").resolve()
        self.assertEqual(preflight.locate_authority_scripts(PLUGIN_ROOT), expected)
        catalog, adapter = preflight.load_authority(PLUGIN_ROOT)
        self.assertEqual(Path(catalog.__file__).resolve(), expected / "catalog.py")
        self.assertEqual(Path(adapter.__file__).resolve(), expected / "plugin.py")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.run_success(Path(tmp)).provider_id, "cliproxyapi")

    def test_versioned_codex_cache_loads_pinned_authority_and_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            consumer, versions_root = self.installed_cache(root, ("1.1.0",))
            expected = (versions_root / "1.1.0" / "scripts").resolve()
            catalog, adapter = preflight.load_authority(consumer)
            self.assertEqual(Path(catalog.__file__).resolve(), expected / "catalog.py")
            self.assertEqual(Path(adapter.__file__).resolve(), expected / "plugin.py")
            result = self.run_success(root / "fixtures", consumer)
            self.assertEqual(result.grok_model, "grok-4.6")
            self.assertEqual(result.gemini_model, "gemini-3.7-flash-high")

    def test_pinned_cache_version_wins_without_guessing_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            consumer, versions_root = self.installed_cache(
                Path(tmp), ("1.0.0", "1.1.0", "1.2.0")
            )
            self.assertEqual(
                preflight.locate_authority_scripts(consumer),
                (versions_root / "1.1.0" / "scripts").resolve(),
            )

    def test_missing_cache_authority_has_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            consumer, _ = self.installed_cache(Path(tmp), ())
            with self.assertRaisesRegex(
                preflight.PreflightError,
                r"requires cliproxy-models 1\.1\.0.*codex plugin add cliproxy-models@cliproxy",
            ):
                preflight.load_authority(consumer)

    def test_incompatible_cache_versions_are_listed_and_not_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            consumer, _ = self.installed_cache(Path(tmp), ("1.0.0", "1.2.0"))
            with self.assertRaises(preflight.PreflightError) as raised:
                preflight.load_authority(consumer)
            message = str(raised.exception)
            self.assertIn("Installed versions: 1.0.0, 1.2.0.", message)
            self.assertIn("Refusing to choose another version.", message)
            self.assertIn("cliproxy-models 1.1.0", message)

    def test_exact_cache_directory_with_wrong_manifest_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            consumer, versions_root = self.installed_cache(Path(tmp), ("1.1.0",))
            manifest_path = versions_root / "1.1.0/.codex-plugin/plugin.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["version"] = "1.1.1"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(
                preflight.PreflightError, r"expected 'cliproxy-models' '1\.1\.0'"
            ):
                preflight.load_authority(consumer)
