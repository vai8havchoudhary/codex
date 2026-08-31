#!/usr/bin/env python3
"""Validate shared CLIProxyAPI authority and modern Codex profile overlays."""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tomllib
import urllib.parse
from pathlib import Path
from types import ModuleType
from typing import Mapping, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from authority_loader import (  # noqa: E402
    DEFAULT_CONFIG,
    GEMINI_PROFILE,
    GROK_PROFILE,
    LUNA_PROFILE,
    KEY_ENV,
    PLUGIN_ROOT,
    DependencyContract,
    PreflightError,
    Result,
    load_authority,
    locate_authority_scripts,
)

__all__ = [
    "DEFAULT_CONFIG",
    "DependencyContract",
    "GEMINI_PROFILE",
    "GROK_PROFILE",
    "KEY_ENV",
    "PLUGIN_ROOT",
    "PreflightError",
    "Result",
    "build_parser",
    "load_authority",
    "locate_authority_scripts",
    "main",
    "profile_path",
    "run_preflight",
]


def profile_path(config: Path, profile_name: str) -> Path:
    return config.parent / f"{profile_name}.config.toml"


def _read_toml(path: Path, label: str) -> dict[str, object]:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise PreflightError(
            f"{label} is missing at {path}; run @cliproxy-models setup first"
        ) from exc
    except OSError as exc:
        raise PreflightError(f"cannot inspect {label} at {path}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise PreflightError(f"{label} must be a regular non-symlink file at {path}")
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise PreflightError(f"cannot read valid {label} at {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise PreflightError(f"unexpected {label} shape in {path}")
    return parsed


def _reject_legacy_profiles(parsed: Mapping[str, object], path: Path) -> None:
    if "profile" in parsed:
        raise PreflightError(
            f"legacy top-level `profile` selector remains in {path}; "
            "rerun @cliproxy-models setup 1.1.0 or migrate it manually"
        )
    if "profiles" in parsed:
        raise PreflightError(
            f"legacy `[profiles.*]` configuration remains in {path}; "
            "Codex 0.134.0+ requires separate `<name>.config.toml` overlays"
        )


def _profile_overlay(config: Path, profile_name: str) -> tuple[str, str]:
    path = profile_path(config, profile_name)
    parsed = _read_toml(path, f"Codex profile overlay {profile_name!r}")
    _reject_legacy_profiles(parsed, path)
    model = parsed.get("model")
    provider = parsed.get("model_provider")
    if not isinstance(model, str) or not model.strip():
        raise PreflightError(f"profile overlay {path} has no top-level `model`")
    if not isinstance(provider, str) or not provider.strip():
        raise PreflightError(f"profile overlay {path} has no top-level `model_provider`")
    return model.strip(), provider.strip()


def _endpoint_identity(value: str, adapter: ModuleType) -> tuple[str, str, int | None, str]:
    normalized = adapter.normalize_provider_base_url(value)
    parsed = urllib.parse.urlsplit(normalized)
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        host = "loopback"
    return parsed.scheme, host, parsed.port, parsed.path.rstrip("/")


def run_preflight(
    *,
    url: str,
    config: Path,
    grok_model: str | None,
    gemini_model: str | None,
    models_response_file: Path | None,
    codex_models_response_file: Path | None,
    timeout: float,
    plugin_root: Path = PLUGIN_ROOT,
    council: str = "grok-gemini",
    luna_model: str | None = None,
    leader_model: str | None = None,
) -> Result:
    catalog, adapter = load_authority(plugin_root)
    if council not in catalog.COUNCILS:
        raise PreflightError("unsupported council; use luna-grok or grok-gemini (Gemini-led native delegation is unsupported)")
    expected_leader, expected_advisor = catalog.COUNCILS[council]
    if leader_model is not None and leader_model != expected_leader:
        raise PreflightError(f"{council} requires leader {expected_leader!r}, not {leader_model!r}; start the matching named profile")
    try:
        base_url = adapter.normalize_provider_base_url(url)
        catalogs = catalog.read_catalogs(
            base_url,
            KEY_ENV,
            models_response_file,
            codex_models_response_file,
            timeout,
        )
        models = catalog.resolve_models(catalogs, grok_model, gemini_model, luna_model)
    except (ValueError, catalog.InstallError) as exc:
        raise PreflightError(str(exc)) from exc

    parsed = _read_toml(config, "Codex base configuration")
    _reject_legacy_profiles(parsed, config)
    configured_grok, grok_provider = _profile_overlay(config, GROK_PROFILE)
    configured_gemini, gemini_provider = _profile_overlay(config, GEMINI_PROFILE)
    configured_luna, luna_provider = _profile_overlay(config, LUNA_PROFILE)
    configured_leader, council_provider = _profile_overlay(config, council)
    if len({grok_provider, gemini_provider, luna_provider, council_provider}) != 1:
        raise PreflightError(
            "All model and selected council profile overlays must use the same CLIProxyAPI provider"
        )
    provider_id = grok_provider

    providers = parsed.get("model_providers")
    if not isinstance(providers, dict):
        raise PreflightError("Codex base configuration has no model_providers table")
    provider = providers.get(provider_id)
    if not isinstance(provider, dict):
        raise PreflightError(
            f"profile provider {provider_id!r} is missing from base config.toml"
        )
    endpoint = provider.get("base_url")
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise PreflightError(f"provider {provider_id!r} has no base_url")
    if provider.get("env_key") != KEY_ENV:
        raise PreflightError(f"provider {provider_id!r} must use env_key {KEY_ENV!r}")
    try:
        configured_identity = _endpoint_identity(endpoint, adapter)
        requested_identity = _endpoint_identity(base_url, adapter)
    except ValueError as exc:
        raise PreflightError(str(exc)) from exc
    if configured_identity != requested_identity:
        raise PreflightError(
            f"provider {provider_id!r} endpoint {endpoint!r} does not match "
            f"validated {base_url!r}"
        )
    if configured_grok != models.grok:
        raise PreflightError(
            f"{GROK_PROFILE}.config.toml points to {configured_grok!r}, "
            f"but live admission resolved {models.grok!r}"
        )
    if configured_gemini != models.gemini:
        raise PreflightError(
            f"{GEMINI_PROFILE}.config.toml points to {configured_gemini!r}, "
            f"but live admission resolved {models.gemini!r}"
        )
    if configured_grok == configured_gemini:
        raise PreflightError(
            "Grok and Gemini profile overlays must resolve to different model IDs"
        )
    if configured_luna != models.luna:
        raise PreflightError(f"{LUNA_PROFILE}.config.toml points to {configured_luna!r}, but live admission resolved {models.luna!r}")
    if configured_leader != expected_leader:
        raise PreflightError(f"{council}.config.toml selects wrong leader; expected {expected_leader!r}")
    if models.grok != "grok-4.6" or (council == "grok-gemini" and models.gemini != expected_advisor):
        raise PreflightError(f"{council} requires its exact leader/advisor IDs; alternate aliases cannot substitute")
    council_config = _read_toml(profile_path(config, council), "council profile")
    if council_config.get("developer_instructions") != catalog.council_instructions(council):
        raise PreflightError(f"{council} profile has missing or mismatched council instructions; rerun setup")
    if "model_instructions_file" in council_config:
        raise PreflightError(f"{council} profile must not override model instructions")
    snapshot = config.parent.resolve() / catalog.MODEL_CATALOG_FILE
    if council_config.get("model_catalog_json") != str(snapshot):
        raise PreflightError(f"{council} must pin the managed model catalog {snapshot}; rerun setup")
    try:
        info = snapshot.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise PreflightError("managed model catalog must be a regular non-symlink file")
        text = snapshot.read_text(encoding="utf-8")
        value = catalog.validate_model_catalog(text)
        current = json.loads(catalog.render_model_catalog(catalogs, text))
        if value != current:
            raise PreflightError("managed model catalog metadata is stale; rerun setup from the live proxy")
    except (OSError, UnicodeError, ValueError, catalog.InstallError) as exc:
        raise PreflightError(f"invalid managed council model catalog: {exc}") from exc
    return Result(provider_id, base_url, configured_grok, configured_gemini,
                  configured_luna, council, expected_leader, expected_advisor)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default=os.environ.get("CLIPROXY_URL", "http://127.0.0.1:8317"),
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--grok-model")
    parser.add_argument("--gemini-model")
    parser.add_argument("--luna-model")
    parser.add_argument("--council", choices=("luna-grok", "grok-gemini"), default="grok-gemini")
    parser.add_argument("--leader-model", help="observed root model; mismatch fails closed")
    parser.add_argument("--models-response-file", type=Path)
    parser.add_argument("--codex-models-response-file", type=Path)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_preflight(
            url=args.url,
            config=args.config,
            grok_model=args.grok_model,
            gemini_model=args.gemini_model,
            luna_model=args.luna_model,
            council=args.council,
            leader_model=args.leader_model,
            models_response_file=args.models_response_file,
            codex_models_response_file=args.codex_models_response_file,
            timeout=args.timeout,
        )
    except PreflightError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        import json

        print(
            json.dumps(
                {
                    "provider_id": result.provider_id,
                    "base_url": result.base_url,
                    "grok_model": result.grok_model,
                    "gemini_model": result.gemini_model,
                    "luna_model": result.luna_model,
                    "council": result.council,
                    "leader_model": result.leader_model,
                    "advisor_model": result.advisor_model,
                    "native_delegation": "unverified: require a real spawn and returned response before editing",
                },
                sort_keys=True,
            )
        )
    else:
        print(f"Provider: {result.provider_id} -> {result.base_url}")
        print(f"Grok: {result.grok_model}")
        print(f"Gemini: {result.gemini_model}")
        print(f"Luna: {result.luna_model}")
        print(f"Council {result.council}: {result.leader_model} -> {result.advisor_model}; native delegation still requires runtime verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
