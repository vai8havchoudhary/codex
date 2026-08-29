#!/usr/bin/env python3
"""Configure Hermes Agent Mixture-of-Agents presets over CLIProxyAPI."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from catalog import (
    DEFAULT_URL,
    KEY_ENV,
    CatalogError,
    environment_key,
    normalize_base_url,
    read_catalogs,
    resolve_models,
)
from hermes_config import (
    GEMINI_PRESET,
    GROK_PRESET,
    HermesError,
    activation_values,
    apply_setup,
    desired_values,
    get_value,
    inspect_status,
    resolve_target,
)

PRESET_ALIASES = {
    "grok": GROK_PRESET,
    "grok-led": GROK_PRESET,
    GROK_PRESET: GROK_PRESET,
    "gemini": GEMINI_PRESET,
    "gemini-led": GEMINI_PRESET,
    GEMINI_PRESET: GEMINI_PRESET,
}


def preset_name(value: str) -> str:
    try:
        return PRESET_ALIASES[value]
    except KeyError as exc:
        raise argparse.ArgumentTypeError(
            "preset must be grok-led, gemini-led, cliproxy-grok-led, or cliproxy-gemini-led"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("CLIPROXY_URL", DEFAULT_URL))
    parser.add_argument("--hermes-bin", default=os.environ.get("HERMES_BIN", "hermes"))
    parser.add_argument("--home", type=Path)
    parser.add_argument("--profile", default=os.environ.get("HERMES_PROFILE"))
    parser.add_argument("--grok-model", help="exact Grok 4.6 alias")
    parser.add_argument("--gemini-model", help="exact Gemini 3.7 Flash alias")
    parser.add_argument("--models-response-file", type=Path)
    parser.add_argument("--codex-models-response-file", type=Path)
    parser.add_argument("--timeout", type=float, default=5.0)

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="validate catalogs and inspect Hermes MoA custody")

    setup = subparsers.add_parser(
        "setup", help="configure both CLIProxyAPI MoA presets transactionally"
    )
    setup.add_argument("preset", type=preset_name, nargs="?", default=GROK_PRESET)
    setup.add_argument(
        "--no-activate",
        action="store_true",
        help="configure presets without switching Hermes' main model to the MoA provider",
    )
    setup.add_argument("--force", action="store_true")
    setup.add_argument(
        "--privacy-filter", choices=("display", "full"), default="display"
    )
    setup.add_argument("--reference-max-tokens", type=int, default=600)
    setup.add_argument("--max-tokens", type=int, default=4096)
    setup.add_argument(
        "--fanout",
        default="user_turn",
        help="user_turn, per_iteration, or every_n:<N>",
    )

    use = subparsers.add_parser(
        "use", help="select an installed MoA preset for new Hermes sessions"
    )
    use.add_argument("preset", type=preset_name)
    use.add_argument("--force", action="store_true")
    return parser


def _load_models(args: argparse.Namespace):
    api_key = environment_key()
    catalogs = read_catalogs(
        normalize_base_url(args.url),
        api_key,
        models_file=args.models_response_file,
        codex_models_file=args.codex_models_response_file,
        timeout=args.timeout,
    )
    return api_key, resolve_models(
        catalogs,
        grok=args.grok_model,
        gemini=args.gemini_model,
    )


def _print_setup(result, *, base_url: str) -> None:
    print(f"CLIProxyAPI endpoint: {base_url}")
    print(f"Hermes provider: cliproxy")
    print(f"Grok-led preset: {GROK_PRESET}")
    print(f"Gemini-led preset: {GEMINI_PRESET}")
    print(f"Grok alias: {result.grok_model}")
    print(f"Gemini alias: {result.gemini_model}")
    print(f"Default MoA preset: {result.active_preset}")
    print(f"Hermes config: {result.config_path}")
    print("Configuration: " + ("changed" if result.changed else "already up to date"))
    if result.backup_path:
        print(f"Backup: {result.backup_path}")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        base_url = normalize_base_url(args.url)
        api_key, models = _load_models(args)
        target = resolve_target(
            executable=args.hermes_bin,
            home=args.home,
            profile=args.profile,
        )
        secrets = (api_key,)

        if args.command == "status":
            status = inspect_status(
                target, base_url=base_url, models=models, secrets=secrets
            )
            print(f"CLIProxyAPI endpoint: {base_url}")
            print(f"Grok alias: {models.grok}")
            print(f"Gemini alias: {models.gemini}")
            print(f"Hermes config: {status['config_path']}")
            print(f"Configured: {'yes' if status['configured'] else 'no'}")
            print(f"Active MoA: {'yes' if status['active'] else 'no'}")
            if status["default_preset"]:
                print(f"Default MoA preset: {status['default_preset']}")
            if status["active_preset"]:
                print(f"Active preset: {status['active_preset']}")
            if status["missing"]:
                print("Missing config keys: " + ", ".join(status["missing"]))
            if status["mismatched"]:
                print("Mismatched config keys: " + ", ".join(status["mismatched"]))
            return 0 if status["configured"] else 2

        if args.command == "setup":
            current_privacy = get_value(
                target, "moa.privacy_filter", secrets=secrets
            )
            privacy_filter = (
                "full" if current_privacy == "full" else args.privacy_filter
            )
            values = desired_values(
                base_url=base_url,
                models=models,
                active_preset=args.preset,
                activate=not args.no_activate,
                privacy_filter=privacy_filter,
                reference_max_tokens=args.reference_max_tokens,
                max_tokens=args.max_tokens,
                fanout=args.fanout,
            )
            result = apply_setup(
                target,
                values,
                force=args.force,
                models=models,
                active_preset=args.preset,
                secrets=secrets,
            )
            _print_setup(result, base_url=base_url)
            print("Restart Hermes or start a new session before using the selected MoA preset.")
            return 0

        if args.command == "use":
            status = inspect_status(
                target, base_url=base_url, models=models, secrets=secrets
            )
            if not status["configured"] and not args.force:
                raise HermesError(
                    "CLIProxyAPI MoA presets are not fully configured; run `setup` first"
                )
            activation = activation_values(args.preset)
            result = apply_setup(
                target,
                activation,
                force=args.force,
                models=models,
                active_preset=args.preset,
                secrets=secrets,
            )
            _print_setup(result, base_url=base_url)
            print("Start a new Hermes session to use the selected MoA preset.")
            return 0

        raise HermesError(f"unsupported command {args.command!r}")
    except (CatalogError, HermesError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
