from __future__ import annotations

import contextlib
import io
import json
import os
import stat
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

import catalog
import install
import plugin
import config_transaction
import test_transaction as fixtures


class NamedCouncilTests(unittest.TestCase):
    def test_derived_catalog_retains_live_metadata_without_synthesis(self):
        entries = tuple({"slug": model, "context_window": 123456,
                         "custom_capability": {"nested": ["untouched", 42]}, "base_instructions": "live metadata"}
                        for model in catalog.CATALOG_MODELS)
        catalogs = catalog.Catalogs(catalog.CATALOG_MODELS, catalog.CATALOG_MODELS, entries)
        value = json.loads(catalog.render_model_catalog(catalogs, None))
        self.assertEqual(value["models"], list(entries))
        self.assertEqual(catalog.render_model_catalog(catalogs, json.dumps(value)), catalog.render_model_catalog(catalogs, None))
        for bad_entries in ((), entries[:-1], entries + (entries[0],)):
            with self.subTest(entries=bad_entries), self.assertRaisesRegex(catalog.InstallError, "metadata entry"):
                catalog.render_model_catalog(catalog.Catalogs(catalog.CATALOG_MODELS, catalog.CATALOG_MODELS, bad_entries), None)

    def test_invalid_or_unmanaged_catalog_is_refused_before_configuration_mutation(self):
        valid = {"_codex_cliproxy_models": 1, "models": [{"slug": item} for item in catalog.CATALOG_MODELS]}
        malformed = ["", "{", "{}", "[]", json.dumps(dict(valid, _codex_cliproxy_models=True)),
                     json.dumps(dict(valid, _codex_cliproxy_models=2)), json.dumps(dict(valid, user_data=True))]
        for slug in (None, [], {}, "another-model", catalog.CATALOG_MODELS[1]):
            changed = json.loads(json.dumps(valid))
            changed["models"][0]["slug"] = slug
            malformed.append(json.dumps(changed))
        malformed.append(json.dumps(dict(valid, models=valid["models"] + [{"slug": "extra"}])))
        for payload in malformed:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                config, args = self.fixture(root)
                target = root / catalog.MODEL_CATALOG_FILE
                target.write_text(payload)
                code, _out, _error = self.run_install(args)
                self.assertEqual(code, 2)
                self.assertFalse(config.exists())
                self.assertEqual(target.read_text(), payload)
                self.assertFalse(list(root.glob("*.bak.*")))

    def test_derived_catalog_symlink_and_nonregular_path_refused(self):
        for kind in ("symlink", "directory"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                config, args = self.fixture(root)
                target = root / catalog.MODEL_CATALOG_FILE
                if kind == "symlink":
                    target.symlink_to(root / "absent")
                else:
                    target.mkdir()
                self.assertEqual(self.run_install(args)[0], 2)
                self.assertFalse(config.exists())

    def test_owned_catalog_write_failure_restores_all_seven_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config, args = self.fixture(root)
            self.assertEqual(self.run_install(args)[0], 0)
            paths = [config, *(root / f"{name}.config.toml" for name in catalog.PROFILE_NAMES), root / catalog.MODEL_CATALOG_FILE]
            for path in paths:
                path.chmod(0o640)
            before = {path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) for path in paths}
            original = config_transaction._replace_text
            failed = False
            def fail_once(path, content, mode):
                nonlocal failed
                if path == paths[-1] and not failed:
                    failed = True
                    raise OSError("injected catalog write failure")
                original(path, content, mode)
            with patch.object(config_transaction, "_replace_text", fail_once):
                self.assertEqual(self.run_install(args)[0], 2)
            self.assertEqual(before, {path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) for path in paths})
            self.assertFalse(list(root.glob("*.bak.*")))

    def test_catalog_concurrent_change_refuses_before_other_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config, args = self.fixture(root)
            original = install._effective_documents
            target = root / catalog.MODEL_CATALOG_FILE
            def concurrent(*values):
                result = original(*values)
                target.write_text("concurrent user bytes")
                return result
            with patch.object(install, "_effective_documents", concurrent):
                code, _out, error = self.run_install(args)
            self.assertEqual(code, 2)
            self.assertIn("concurrently", error)
            self.assertFalse(config.exists())
            self.assertEqual(target.read_text(), "concurrent user bytes")

    def fixture(self, root):
        helper = fixtures.EndToEndTests()
        config = root / "config.toml"
        openai, codex = helper._offline_files(root)
        return config, helper._args(config, openai, codex)

    def run_install(self, args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = install.main(args)
        return code, output.getvalue(), errors.getvalue()

    def test_exact_luna_required_in_both_catalogs_no_advisor_substitution(self):
        base = ("grok-4.6", "gemini-3.7-flash-high")
        for left, right in ((base, base), (base + (catalog.LUNA_MODEL,), base),
                            (base, base + (catalog.LUNA_MODEL,)),
                            (base + ("gpt-5.6-luna-advisor",), base + ("gpt-5.6-luna-advisor",))):
            with self.subTest(left=left, right=right), self.assertRaisesRegex(catalog.InstallError, "both CLIProxyAPI catalogs"):
                catalog.resolve_models(catalog.Catalogs(left, right))
        ids = base + (catalog.LUNA_MODEL, "gpt-5.6-luna-advisor")
        self.assertEqual(catalog.resolve_models(catalog.Catalogs(ids, ids)).luna, catalog.LUNA_MODEL)
        with self.assertRaisesRegex(catalog.InstallError, "Luna requires exact"):
            catalog.resolve_models(catalog.Catalogs(ids, ids), luna="gpt-5.6-luna-advisor")

    def test_seven_documents_named_leaders_instructions_modes_and_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config, args = self.fixture(root)
            config.write_text('model = "grok-4.6"\n# user comment\n')
            self.assertEqual(self.run_install(args)[0], 0)
            paths = [config, *(root / f"{name}.config.toml" for name in catalog.PROFILE_NAMES)]
            paths.append(root / catalog.MODEL_CATALOG_FILE)
            self.assertEqual(len(paths), 7)
            before = {path: path.read_bytes() for path in paths}
            self.assertEqual(set(tomllib.loads(config.read_text())["model_providers"]), {"cliproxyapi"})
            for name, (leader, _reviewer) in catalog.COUNCILS.items():
                overlay = tomllib.loads((root / f"{name}.config.toml").read_text())
                self.assertEqual(overlay["model"], leader)
                self.assertEqual(overlay["model_provider"], "cliproxyapi")
                self.assertEqual(overlay["developer_instructions"], catalog.council_instructions(name))
                self.assertEqual(overlay["model_catalog_json"], str(root / catalog.MODEL_CATALOG_FILE))
            self.assertEqual(set(model["slug"] for model in json.loads(paths[-1].read_text())["models"]), set(catalog.CATALOG_MODELS))
            self.assertNotIn("model_catalog_json", tomllib.loads(config.read_text()))
            for path in paths:
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            backups = sorted(root.glob("*.bak.*"))
            self.assertEqual(self.run_install(args)[0], 0)
            self.assertEqual(before, {path: path.read_bytes() for path in paths})
            self.assertEqual(backups, sorted(root.glob("*.bak.*")))

    def test_luna_default_and_wrapper_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, args = self.fixture(Path(tmp))
            args[-1] = "luna"
            self.assertEqual(self.run_install(args)[0], 0)
            self.assertEqual(tomllib.loads(config.read_text())["model"], catalog.LUNA_MODEL)
        for command in ("setup", "use"):
            parsed = plugin.build_parser().parse_args(["--luna-model", catalog.LUNA_MODEL, command, "luna"])
            forwarded = plugin.installer_args(parsed)
            self.assertEqual(forwarded[-2:], ["--default", "luna"])
            self.assertIn("--luna-model", forwarded)

    def test_named_profile_unmanaged_collisions_refuse_all_writes(self):
        for name in ("luna-grok", "grok-gemini"):
            for key in ("model", "model_provider", "developer_instructions", "model_instructions_file", "model_catalog_json"):
                with self.subTest(name=name, key=key), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    config, args = self.fixture(root)
                    target = root / f"{name}.config.toml"
                    original = f'{key} = "user-owned"\n'
                    target.write_text(original)
                    code, _out, error = self.run_install(args)
                    self.assertEqual(code, 2)
                    self.assertIn("unmanaged", error)
                    self.assertFalse(config.exists())
                    self.assertEqual(target.read_text(), original)
                    self.assertFalse(list(root.glob("*.bak.*")))

    def test_new_profile_symlink_and_directory_refused_without_partial_files(self):
        for name in (catalog.LUNA_PROFILE, "luna-grok", "grok-gemini"):
            for kind in ("symlink", "directory"):
                with self.subTest(name=name, kind=kind), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    config, args = self.fixture(root)
                    target = root / f"{name}.config.toml"
                    if kind == "symlink":
                        target.symlink_to(root / "absent.toml")
                    else:
                        target.mkdir()
                    self.assertEqual(self.run_install(args)[0], 2)
                    self.assertFalse(config.exists())

    def test_each_new_profile_write_failure_rolls_back_exact_bytes_and_modes(self):
        for name in (catalog.LUNA_PROFILE, "luna-grok", "grok-gemini"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                config, args = self.fixture(root)
                paths = [config, *(root / f"{item}.config.toml" for item in catalog.PROFILE_NAMES)]
                for index, path in enumerate(paths):
                    path.write_text(f"# user comment {index}\n")
                    path.chmod(0o640)
                before = {path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) for path in paths}
                target = root / f"{name}.config.toml"
                original = config_transaction._replace_text
                failed = False
                def fail_once(path, content, mode):
                    nonlocal failed
                    if path == target and not failed:
                        failed = True
                        raise OSError("injected named overlay write failure")
                    original(path, content, mode)
                with patch.object(config_transaction, "_replace_text", fail_once):
                    code, _out, error = self.run_install(args)
                self.assertEqual(code, 2)
                self.assertIn("rolled back", error)
                self.assertEqual(before, {path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) for path in paths})
                self.assertFalse(list(root.glob("*.bak.*")))

    def test_post_validation_failure_removes_new_profiles_and_restores_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config, args = self.fixture(root)
            config.write_text("# preserve\n")
            config.chmod(0o640)
            with patch.object(install, "_post_validate", side_effect=catalog.InstallError("injected post-validation failure")):
                self.assertEqual(self.run_install(args)[0], 2)
            self.assertEqual(config.read_text(), "# preserve\n")
            self.assertEqual(stat.S_IMODE(config.stat().st_mode), 0o640)
            self.assertFalse(list(root.glob("*.config.toml")))
            self.assertFalse((root / catalog.MODEL_CATALOG_FILE).exists())
            self.assertFalse(list(root.glob("*.bak.*")))
