#!/usr/bin/env python3
"""CLIProxyAPI Models plugin entry point for Codex."""
from __future__ import annotations

import argparse
import importlib
import os
import sys
import urllib.parse
from pathlib import Path
from typing import Sequence

DEFAULT_URL = "http://127.0.0.1:8317"
KEY_ENV = "CLIPROXY_API_KEY"
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def normalize_provider_base_url(raw: str) -> str:
    value = raw.strip().rstrip("/")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("CLIPROXY_URL must be an absolute http:// or https:// URL")
    if parsed.username or parsed.password:
        raise ValueError("CLIPROXY_URL must not embed credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("CLIPROXY_URL must not contain a query string or fragment")
    path = parsed.path.rstrip("/")
    if path not in {"", "/v1"}:
        raise ValueError("CLIPROXY_URL path must be empty or /v1")
    if parsed.scheme == "http" and parsed.hostname.lower() not in LOOPBACK_HOSTS:
        raise ValueError("plain HTTP is allowed only for localhost or loopback CLIProxyAPI endpoints")
    origin = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    return f"{origin}/v1"


def load_installer():
    script_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(script_dir))
    return importlib.import_module("install")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("CLIPROXY_URL", DEFAULT_URL))
    parser.add_argument("--config", type=Path)
    parser.add_argument("--grok-model")
    parser.add_argument("--gemini-model")
    parser.add_argument("--luna-model")
    parser.add_argument("--models-response-file", type=Path)
    parser.add_argument("--codex-models-response-file", type=Path)
    parser.add_argument("--timeout", type=float, default=5.0)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="validate catalogs without changing the active Codex provider")
    setup = subparsers.add_parser("setup", help="install or repair the managed provider and profiles")
    setup.add_argument("model", choices=("grok", "gemini", "luna"), nargs="?", default="grok")
    use = subparsers.add_parser("use", help="switch the default model for new Codex sessions")
    use.add_argument("model", choices=("grok", "gemini", "luna"))
    return parser


def installer_args(args: argparse.Namespace) -> list[str]:
    values = [
        "--base-url",
        normalize_provider_base_url(args.url),
        "--api-key-env",
        KEY_ENV,
        "--timeout",
        str(args.timeout),
    ]
    if args.config is not None:
        values += ["--config", str(args.config)]
    for flag, value in (
        ("--grok-model", args.grok_model),
        ("--gemini-model", args.gemini_model),
        ("--luna-model", args.luna_model),
        ("--models-response-file", args.models_response_file),
        ("--codex-models-response-file", args.codex_models_response_file),
    ):
        if value is not None:
            values += [flag, str(value)]
    if args.command == "status":
        return values + ["--profiles-only", "--dry-run"]
    return values + ["--default", args.model]


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(load_installer().main(installer_args(args)))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
