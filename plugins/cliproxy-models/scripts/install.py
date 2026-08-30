#!/usr/bin/env python3
"""Install CLIProxyAPI Grok 4.6 and Gemini 3.7 Flash for Codex Desktop.

CLIProxyAPI remains the only owner of upstream accounts, credentials, quota
balancing, and failover. Codex receives one provider endpoint and stable aliases.
Python 3.11+; standard library only.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

from catalog import (
    DEFAULT_BASE_URL,
    DEFAULT_CONFIG,
    DEFAULT_KEY_ENV,
    DEFAULT_PROVIDER_ID,
    GEMINI_PROFILE,
    GROK_PROFILE,
    BEGIN,
    END,
    Catalogs,
    InstallError,
    Models,
    Provider,
    choose_provider,
    extract_codex_slugs,
    extract_openai_ids,
    parse_toml,
    read_catalogs,
    resolve_models,
)
from config_edit import (
    ConfigDocuments,
    FileState,
    PlannedFile,
    profile_path,
    read_state,
    render_documents,
    transactional_write,
    validate_documents,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="add CLIProxyAPI Grok 4.6 and Gemini 3.7 Flash to Codex Desktop"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--provider-id", default=DEFAULT_PROVIDER_ID)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("CLIPROXY_BASE_URL", DEFAULT_BASE_URL),
    )
    default_env = os.environ.get("CLIPROXY_API_KEY_ENV")
    if default_env is None and os.environ.get(DEFAULT_KEY_ENV):
        default_env = DEFAULT_KEY_ENV
    parser.add_argument(
        "--api-key-env",
        default=default_env,
        help="environment-variable name containing the proxy token",
    )
    parser.add_argument("--grok-model", help="exact Grok 4.6 alias")
    parser.add_argument("--gemini-model", help="exact Gemini 3.7 Flash alias")
    parser.add_argument("--models-response-file", type=Path, help="offline /v1/models JSON")
    parser.add_argument(
        "--codex-models-response-file",
        type=Path,
        help="offline Codex catalog JSON",
    )
    parser.add_argument(
        "--profiles-only",
        action="store_true",
        help="do not activate CLIProxyAPI as the Desktop catalog provider",
    )
    parser.add_argument(
        "--default",
        choices=("preserve", "grok", "gemini"),
        default="preserve",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print-effective", action="store_true")
    parser.add_argument("--timeout", type=float, default=5.0)
    return parser


def _effective_documents(
    config: Path,
    base_state: FileState,
    provider: Provider,
    models: Models,
    activate: bool,
    default_model: str | None,
) -> tuple[list[PlannedFile], ConfigDocuments]:
    grok_path = profile_path(config, GROK_PROFILE)
    gemini_path = profile_path(config, GEMINI_PROFILE)
    grok_state = read_state(grok_path, f"Codex profile {GROK_PROFILE}")
    gemini_state = read_state(gemini_path, f"Codex profile {GEMINI_PROFILE}")
    documents = render_documents(
        base_original=base_state.content,
        grok_original=grok_state.content,
        gemini_original=gemini_state.content,
        provider=provider,
        models=models,
        activate_provider=activate,
        default_model=default_model,
    )
    plans = [
        PlannedFile(base_state, documents.base),
        PlannedFile(grok_state, documents.grok),
        PlannedFile(gemini_state, documents.gemini),
    ]
    return plans, documents


def _post_validate(
    plans: Sequence[PlannedFile],
    provider: Provider,
    models: Models,
    activate: bool,
) -> None:
    contents = {plan.state.path: plan.state.path.read_text(encoding="utf-8") for plan in plans}
    validate_documents(
        ConfigDocuments(
            base=contents[plans[0].state.path],
            grok=contents[plans[1].state.path],
            gemini=contents[plans[2].state.path],
        ),
        provider,
        models,
        activate,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        base_state = read_state(args.config, "Codex base configuration")
        parsed = parse_toml(base_state.content, str(args.config))
        provider = choose_provider(
            parsed,
            args.provider_id,
            args.base_url,
            args.api_key_env,
        )
        catalogs = read_catalogs(
            provider.base_url,
            provider.env_key,
            args.models_response_file,
            args.codex_models_response_file,
            args.timeout,
        )
        models = resolve_models(catalogs, args.grok_model, args.gemini_model)
        activate = not args.profiles_only
        current = parsed.get("model")
        if args.default == "grok":
            default_model = models.grok
        elif args.default == "gemini":
            default_model = models.gemini
        elif isinstance(current, str) and current:
            if activate and current not in catalogs.codex_slugs:
                raise InstallError(
                    f"current Codex model {current!r} is not published by CLIProxyAPI; "
                    "choose --default grok, --default gemini, or --profiles-only"
                )
            default_model = None
        else:
            default_model = models.grok if activate else None

        plans, documents = _effective_documents(
            args.config,
            base_state,
            provider,
            models,
            activate,
            default_model,
        )
        changed = [plan for plan in plans if plan.changed]
        print(f"Provider: {provider.provider_id} -> {provider.base_url}")
        print(f"Profile {GROK_PROFILE}: {models.grok}")
        print(f"Profile {GEMINI_PROFILE}: {models.gemini}")
        print(
            "Desktop catalog provider: "
            + ("unchanged" if args.profiles_only else provider.provider_id)
        )
        print(
            "Configuration: "
            + (f"would change {len(changed)} file(s)" if changed else "already up to date")
        )
        if args.print_effective:
            print("\n--- effective config.toml ---")
            print(documents.base, end="")
            print(f"\n--- effective {GROK_PROFILE}.config.toml ---")
            print(documents.grok, end="")
            print(f"\n--- effective {GEMINI_PROFILE}.config.toml ---")
            print(documents.gemini, end="")
        if args.dry_run or not changed:
            return 0

        backups = transactional_write(
            plans,
            lambda: _post_validate(plans, provider, models, activate),
        )
        for plan in plans:
            if plan.changed:
                print(f"Wrote: {plan.state.path}")
            backup = backups.get(plan.state.path)
            if backup:
                print(f"Backup: {backup}")
        return 0
    except InstallError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
