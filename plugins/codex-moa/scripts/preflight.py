#!/usr/bin/env python3
"""Validate the shared CLIProxyAPI model authority before native Codex councils."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tomllib
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Sequence

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PLUGINS = PLUGIN_ROOT.parent
CLIPROXY_SCRIPTS = MARKETPLACE_PLUGINS / "cliproxy-models" / "scripts"
DEFAULT_CONFIG = Path.home() / ".codex" / "config.toml"
KEY_ENV = "CLIPROXY_API_KEY"
GROK_PROFILE = "cliproxy-grok-4-6"
GEMINI_PROFILE = "cliproxy-gemini-3-7-flash"


class PreflightError(RuntimeError):
    """A fail-closed native-council preflight error."""


@dataclass(frozen=True)
class Result:
    provider_id: str
    base_url: str
    grok_model: str
    gemini_model: str


def _load_module(name: str, path: Path) -> ModuleType:
    if not path.is_file():
        raise PreflightError(
            "cliproxy-models is required beside codex-moa in the same marketplace installation"
        )
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise PreflightError(f"cannot load shared model authority at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_authority() -> tuple[ModuleType, ModuleType]:
    catalog = _load_module("codex_moa_cliproxy_catalog", CLIPROXY_SCRIPTS / "catalog.py")
    adapter = _load_module("codex_moa_cliproxy_adapter", CLIPROXY_SCRIPTS / "plugin.py")
    return catalog, adapter


def _read_config(path: Path) -> dict[str, object]:
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PreflightError(
            f"Codex configuration {path} does not exist; run @cliproxy-models setup first"
        ) from exc
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise PreflightError(f"cannot read valid Codex configuration {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise PreflightError(f"unexpected Codex configuration shape in {path}")
    return parsed


def _profile(parsed: dict[str, object], profile_name: str) -> tuple[str, str]:
    profiles = parsed.get("profiles")
    if not isinstance(profiles, dict):
        raise PreflightError("Codex configuration has no profiles table")
    profile = profiles.get(profile_name)
    if not isinstance(profile, dict):
        raise PreflightError(f"required Codex profile {profile_name!r} is missing")
    model = profile.get("model")
    provider = profile.get("model_provider")
    if not isinstance(model, str) or not model.strip():
        raise PreflightError(f"profile {profile_name!r} has no model")
    if not isinstance(provider, str) or not provider.strip():
        raise PreflightError(f"profile {profile_name!r} has no model_provider")
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
) -> Result:
    catalog, adapter = load_authority()
    try:
        base_url = adapter.normalize_provider_base_url(url)
        catalogs = catalog.read_catalogs(
            base_url,
            KEY_ENV,
            models_response_file,
            codex_models_response_file,
            timeout,
        )
        models = catalog.resolve_models(catalogs, grok_model, gemini_model)
    except (ValueError, catalog.InstallError) as exc:
        raise PreflightError(str(exc)) from exc

    parsed = _read_config(config)
    configured_grok, grok_provider = _profile(parsed, GROK_PROFILE)
    configured_gemini, gemini_provider = _profile(parsed, GEMINI_PROFILE)
    if grok_provider != gemini_provider:
        raise PreflightError("Grok and Gemini profiles must use the same CLIProxyAPI provider")
    provider_id = grok_provider

    providers = parsed.get("model_providers")
    if not isinstance(providers, dict):
        raise PreflightError("Codex configuration has no model_providers table")
    provider = providers.get(provider_id)
    if not isinstance(provider, dict):
        raise PreflightError(f"profile provider {provider_id!r} is missing")
    endpoint = provider.get("base_url")
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise PreflightError(f"provider {provider_id!r} has no base_url")
    if provider.get("env_key") != KEY_ENV:
        raise PreflightError(
            f"provider {provider_id!r} must use env_key {KEY_ENV!r}"
        )
    try:
        configured_identity = _endpoint_identity(endpoint, adapter)
        requested_identity = _endpoint_identity(base_url, adapter)
    except ValueError as exc:
        raise PreflightError(str(exc)) from exc
    if configured_identity != requested_identity:
        raise PreflightError(
            f"provider {provider_id!r} endpoint {endpoint!r} does not match validated {base_url!r}"
        )
    if configured_grok != models.grok:
        raise PreflightError(
            f"{GROK_PROFILE} points to {configured_grok!r}, but live admission resolved {models.grok!r}"
        )
    if configured_gemini != models.gemini:
        raise PreflightError(
            f"{GEMINI_PROFILE} points to {configured_gemini!r}, but live admission resolved {models.gemini!r}"
        )
    if configured_grok == configured_gemini:
        raise PreflightError("Grok and Gemini profiles must resolve to different model IDs")
    return Result(provider_id, base_url, configured_grok, configured_gemini)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("CLIPROXY_URL", "http://127.0.0.1:8317"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--grok-model")
    parser.add_argument("--gemini-model")
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
            models_response_file=args.models_response_file,
            codex_models_response_file=args.codex_models_response_file,
            timeout=args.timeout,
        )
    except PreflightError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    payload = {
        "provider_id": result.provider_id,
        "base_url": result.base_url,
        "grok_model": result.grok_model,
        "gemini_model": result.gemini_model,
    }
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"Provider: {result.provider_id} -> {result.base_url}")
        print(f"Grok advisor/writer model: {result.grok_model}")
        print(f"Gemini advisor/writer model: {result.gemini_model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
