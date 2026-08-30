"""Release-bound cliproxy-models authority discovery for codex-moa."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_CONTRACT = "authority.json"
PLUGIN_MANIFEST = Path(".codex-plugin") / "plugin.json"
DEFAULT_CONFIG = Path.home() / ".codex" / "config.toml"
KEY_ENV = "CLIPROXY_API_KEY"
GROK_PROFILE = "cliproxy-grok-4-6"
GEMINI_PROFILE = "cliproxy-gemini-3-7-flash"
PLUGIN_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class PreflightError(RuntimeError):
    """A fail-closed native-council preflight error."""


@dataclass(frozen=True)
class PluginPin:
    name: str
    version: str


@dataclass(frozen=True)
class AuthorityPin:
    name: str
    version: str
    scripts: tuple[str, ...]


@dataclass(frozen=True)
class DependencyContract:
    marketplace: str
    release_name: str
    release_version: str
    consumer: PluginPin
    authority: AuthorityPin


@dataclass(frozen=True)
class Result:
    provider_id: str
    base_url: str
    grok_model: str
    gemini_model: str


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PreflightError(f"{label} is missing at {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise PreflightError(f"cannot read valid {label} at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PreflightError(f"{label} at {path} must be a JSON object")
    return value


def _plugin_pin(value: object, label: str) -> PluginPin:
    if not isinstance(value, dict):
        raise PreflightError(f"{label} must be a JSON object")
    name = value.get("name")
    version = value.get("version")
    if not isinstance(name, str) or PLUGIN_ID_RE.fullmatch(name) is None:
        raise PreflightError(f"{label}.name must be a valid plugin identifier")
    if not isinstance(version, str) or SEMVER_RE.fullmatch(version) is None:
        raise PreflightError(f"{label}.version must be stable semantic versioning")
    return PluginPin(name, version)


def _plugin_manifest(root: Path, expected: PluginPin, label: str) -> dict[str, Any]:
    manifest_path = root / PLUGIN_MANIFEST
    manifest = _read_json_object(manifest_path, f"{label} manifest")
    if manifest.get("name") != expected.name or manifest.get("version") != expected.version:
        raise PreflightError(
            f"{label} manifest at {manifest_path} is "
            f"{manifest.get('name')!r} {manifest.get('version')!r}; "
            f"expected {expected.name!r} {expected.version!r}"
        )
    return manifest


def _load_contract(plugin_root: Path) -> DependencyContract:
    raw = _read_json_object(
        plugin_root / AUTHORITY_CONTRACT,
        "model-authority contract",
    )
    if raw.get("schema") != 1:
        raise PreflightError("model-authority contract schema must be exactly 1")
    marketplace = raw.get("marketplace")
    release = raw.get("release")
    if not isinstance(marketplace, str) or PLUGIN_ID_RE.fullmatch(marketplace) is None:
        raise PreflightError("model-authority contract marketplace must be a valid identifier")
    if not isinstance(release, dict):
        raise PreflightError("model-authority contract release must be a JSON object")
    release_name = release.get("name")
    release_version = release.get("version")
    if not isinstance(release_name, str) or PLUGIN_ID_RE.fullmatch(release_name) is None:
        raise PreflightError("model-authority contract release.name must be a valid identifier")
    if not isinstance(release_version, str) or SEMVER_RE.fullmatch(release_version) is None:
        raise PreflightError("model-authority contract release.version must be stable semantic versioning")

    consumer = _plugin_pin(raw.get("consumer"), "model-authority contract consumer")
    authority_raw = raw.get("authority")
    authority_pin = _plugin_pin(authority_raw, "model-authority contract authority")
    if not isinstance(authority_raw, dict):
        raise PreflightError("model-authority contract authority must be a JSON object")
    scripts_raw = authority_raw.get("scripts")
    if not isinstance(scripts_raw, list) or not scripts_raw:
        raise PreflightError("model-authority contract authority.scripts must be a non-empty list")
    scripts: list[str] = []
    for value in scripts_raw:
        if (
            not isinstance(value, str)
            or Path(value).name != value
            or value in {".", ".."}
            or not value.endswith(".py")
        ):
            raise PreflightError(
                "model-authority contract script names must be plain Python filenames"
            )
        if value in scripts:
            raise PreflightError(f"duplicate model-authority script {value!r}")
        scripts.append(value)

    contract = DependencyContract(
        marketplace=marketplace,
        release_name=release_name,
        release_version=release_version,
        consumer=consumer,
        authority=AuthorityPin(
            authority_pin.name,
            authority_pin.version,
            tuple(scripts),
        ),
    )
    _plugin_manifest(plugin_root, contract.consumer, "codex-moa consumer")
    return contract


def _validate_authority_root(
    root: Path,
    contract: DependencyContract,
    label: str,
) -> Path:
    if root.is_symlink():
        raise PreflightError(f"{label} model authority directory must not be a symlink: {root}")
    if not root.is_dir():
        raise PreflightError(f"{label} model authority directory is missing at {root}")
    _plugin_manifest(
        root,
        PluginPin(contract.authority.name, contract.authority.version),
        label,
    )
    scripts = root / "scripts"
    if not scripts.is_dir() or scripts.is_symlink():
        raise PreflightError(f"{label} model authority scripts directory is unsafe at {scripts}")
    missing = [
        name
        for name in contract.authority.scripts
        if not (scripts / name).is_file() or (scripts / name).is_symlink()
    ]
    if missing:
        raise PreflightError(
            f"{label} model authority {root} is missing regular required scripts: "
            + ", ".join(missing)
        )
    return scripts.resolve()


def _validate_source_release(repo_root: Path, contract: DependencyContract) -> None:
    release_path = repo_root / "release.json"
    release = _read_json_object(release_path, "source release contract")
    plugins = release.get("plugins")
    if (
        release.get("name") != contract.release_name
        or release.get("version") != contract.release_version
        or not isinstance(plugins, dict)
        or plugins.get(contract.consumer.name) != contract.consumer.version
        or plugins.get(contract.authority.name) != contract.authority.version
    ):
        raise PreflightError(
            f"source release contract {release_path} does not match "
            f"{contract.release_name} {contract.release_version} with "
            f"{contract.consumer.name} {contract.consumer.version} and "
            f"{contract.authority.name} {contract.authority.version}"
        )


def _source_candidate(plugin_root: Path, contract: DependencyContract) -> Path | None:
    plugins_root = plugin_root.parent
    release_path = plugins_root.parent / "release.json"
    candidate = plugins_root / contract.authority.name
    if not release_path.exists() and not candidate.exists():
        return None
    if not release_path.is_file() or release_path.is_symlink():
        raise PreflightError(
            f"found adjacent {contract.authority.name} at {candidate}, but source release "
            f"contract {release_path} is missing or unsafe; refusing an unbound authority"
        )
    _validate_source_release(plugins_root.parent, contract)
    return _validate_authority_root(candidate, contract, "source-tree")


def _installed_versions(root: Path) -> tuple[str, ...]:
    if not root.is_dir():
        return ()
    if root.is_symlink():
        raise PreflightError(f"installed model-authority versions path is a symlink: {root}")
    try:
        children = tuple(root.iterdir())
    except OSError as exc:
        raise PreflightError(f"cannot inspect installed model-authority versions at {root}: {exc}") from exc
    values = [
        child.name
        for child in children
        if child.is_dir()
        and not child.is_symlink()
        and SEMVER_RE.fullmatch(child.name) is not None
    ]
    return tuple(sorted(values, key=lambda value: tuple(int(part) for part in value.split("."))))


def _cache_candidate(plugin_root: Path, contract: DependencyContract) -> Path | None:
    if plugin_root.name != contract.consumer.version or plugin_root.parent.name != contract.consumer.name:
        return None
    marketplace_root = plugin_root.parent.parent
    if marketplace_root.name != contract.marketplace:
        raise PreflightError(
            f"installed {contract.consumer.name} cache belongs to marketplace "
            f"{marketplace_root.name!r}; expected {contract.marketplace!r}"
        )
    versions_root = marketplace_root / contract.authority.name
    candidate = versions_root / contract.authority.version
    if candidate.is_dir() and not candidate.is_symlink():
        return _validate_authority_root(candidate, contract, "installed-cache")
    installed = _installed_versions(versions_root)
    suffix = (
        " Installed versions: " + ", ".join(installed) + "."
        if installed
        else " No versions are installed."
    )
    raise PreflightError(
        f"{contract.consumer.name} {contract.consumer.version} requires "
        f"{contract.authority.name} {contract.authority.version} from marketplace "
        f"{contract.marketplace!r}, but the exact authority is missing at {candidate}."
        f"{suffix} Refusing to choose another version. Run "
        f"`codex plugin marketplace upgrade {contract.marketplace}` and "
        f"`codex plugin add {contract.authority.name}@{contract.marketplace}`, "
        "then verify both required versions are enabled."
    )


def locate_authority_scripts(plugin_root: Path = PLUGIN_ROOT) -> Path:
    root = Path(plugin_root).resolve()
    contract = _load_contract(root)
    candidates: list[Path] = []
    for candidate in (
        _source_candidate(root, contract),
        _cache_candidate(root, contract),
    ):
        if candidate is not None and candidate not in candidates:
            candidates.append(candidate)
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise PreflightError(
            "multiple compatible cliproxy-models authorities were found: "
            + ", ".join(str(path) for path in candidates)
            + "; refusing to choose"
        )
    raise PreflightError(
        f"cannot locate {contract.authority.name} {contract.authority.version}. "
        "Supported layouts are a release-bound source checkout "
        "`plugins/codex-moa` + `plugins/cliproxy-models`, or the Codex cache "
        f"`<cache>/{contract.marketplace}/{contract.authority.name}/"
        f"{contract.authority.version}` beside the installed consumer."
    )


def _load_module(name: str, path: Path) -> ModuleType:
    if not path.is_file() or path.is_symlink():
        raise PreflightError(f"cannot load shared model authority at {path}")
    digest = hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:16]
    module_name = f"{name}_{digest}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise PreflightError(f"cannot load shared model authority at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        raise PreflightError(f"cannot load shared model authority at {path}: {exc}") from exc
    return module


def load_authority(plugin_root: Path = PLUGIN_ROOT) -> tuple[ModuleType, ModuleType]:
    scripts = locate_authority_scripts(plugin_root)
    catalog = _load_module("codex_moa_cliproxy_catalog", scripts / "catalog.py")
    adapter = _load_module("codex_moa_cliproxy_adapter", scripts / "plugin.py")
    return catalog, adapter


def profile_path(config: Path, profile_name: str) -> Path:
    return config.parent / f"{profile_name}.config.toml"

