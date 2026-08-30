from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SOURCE_AUTHORITY_ROOT = PLUGIN_ROOT.parent / "cliproxy-models"
MODULE_PATH = PLUGIN_ROOT / "scripts" / "preflight.py"
SPEC = importlib.util.spec_from_file_location("codex_moa_preflight_test", MODULE_PATH)
assert SPEC and SPEC.loader
preflight = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = preflight
SPEC.loader.exec_module(preflight)


class PreflightTestCase(unittest.TestCase):
    def files(
        self,
        root: Path,
        openai_ids: list[str],
        codex_ids: list[str],
    ) -> tuple[Path, Path]:
        root.mkdir(parents=True, exist_ok=True)
        openai = root / "models.json"
        codex = root / "codex-models.json"
        openai.write_text(
            json.dumps({"data": [{"id": value} for value in openai_ids]}),
            encoding="utf-8",
        )
        codex.write_text(
            json.dumps({"models": [{"slug": value} for value in codex_ids]}),
            encoding="utf-8",
        )
        return openai, codex

    def config(
        self,
        root: Path,
        *,
        gemini: str = "gemini-3.7-flash-high",
        grok_provider: str = "cliproxyapi",
        gemini_provider: str = "cliproxyapi",
    ) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        path = root / "config.toml"
        path.write_text(
            '''model = "grok-4.6"
model_provider = "cliproxyapi"

[model_providers.cliproxyapi]
name = "CLIProxyAPI"
base_url = "http://127.0.0.1:8317/v1"
env_key = "CLIPROXY_API_KEY"
wire_api = "responses"
requires_openai_auth = false
''',
            encoding="utf-8",
        )
        preflight.profile_path(path, preflight.GROK_PROFILE).write_text(
            f'model = "grok-4.6"\nmodel_provider = "{grok_provider}"\n',
            encoding="utf-8",
        )
        preflight.profile_path(path, preflight.GEMINI_PROFILE).write_text(
            f'model = "{gemini}"\nmodel_provider = "{gemini_provider}"\n',
            encoding="utf-8",
        )
        return path

    def copy_plugin(self, source: Path, destination: Path, version: str | None = None) -> None:
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        if version is not None:
            manifest_path = destination / ".codex-plugin/plugin.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["version"] = version
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    def installed_cache(
        self,
        root: Path,
        authority_versions: tuple[str, ...],
    ) -> tuple[Path, Path]:
        marketplace = root / "cache" / "cliproxy"
        consumer = marketplace / "codex-moa" / "2.0.0"
        self.copy_plugin(PLUGIN_ROOT, consumer)
        versions_root = marketplace / "cliproxy-models"
        for version in authority_versions:
            self.copy_plugin(SOURCE_AUTHORITY_ROOT, versions_root / version, version=version)
        return consumer, versions_root

    def run_success(self, root: Path, plugin_root: Path = PLUGIN_ROOT):
        ids = ["grok-4.6", "gemini-3.7-flash-high"]
        openai, codex = self.files(root, ids, ids)
        return preflight.run_preflight(
            url="http://127.0.0.1:8317",
            config=self.config(root),
            grok_model="grok-4.6",
            gemini_model="gemini-3.7-flash-high",
            models_response_file=openai,
            codex_models_response_file=codex,
            timeout=1,
            plugin_root=plugin_root,
        )
