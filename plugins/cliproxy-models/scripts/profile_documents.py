"""Render the base provider and modern Codex profile overlay documents."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from catalog import (
    BEGIN,
    END,
    GEMINI_PROFILE,
    GROK_PROFILE,
    LUNA_PROFILE,
    COUNCILS,
    council_instructions,
    validate_council_installation,
    InstallError,
    Models,
    Provider,
    parse_toml,
)
from toml_edit import (
    PROFILE_BEGIN,
    PROFILE_END,
    _first_table,
    _managed_region,
    _remove_top_level_key,
    has_table,
    upsert_top_level,
)


@dataclass(frozen=True)
class ConfigDocuments:
    base: str
    grok: str
    gemini: str
    luna: str
    luna_grok: str
    grok_gemini: str


def profile_path(config: Path, profile_name: str) -> Path:
    return config.parent / f"{profile_name}.config.toml"


def _validate_legacy_block(
    managed: str | None,
    provider_id: str,
) -> bool:
    if managed is None:
        return False
    parsed = parse_toml(managed, "existing CLIProxyAPI managed block")
    unexpected = set(parsed) - {"model_providers", "profiles"}
    if unexpected:
        raise InstallError(
            "CLIProxyAPI managed block contains unexpected configuration roots: "
            + ", ".join(sorted(unexpected))
        )
    providers = parsed.get("model_providers", {})
    if providers is not None and not isinstance(providers, Mapping):
        raise InstallError("managed model_providers entry is not a TOML table")
    provider_ids = set(providers) if isinstance(providers, Mapping) else set()
    if provider_ids - {provider_id}:
        raise InstallError(
            "CLIProxyAPI managed block contains an unexpected provider: "
            + ", ".join(sorted(str(value) for value in provider_ids - {provider_id}))
        )
    profiles = parsed.get("profiles", {})
    if profiles is not None and not isinstance(profiles, Mapping):
        raise InstallError("managed profiles entry is not a TOML table")
    profile_ids = set(profiles) if isinstance(profiles, Mapping) else set()
    unexpected_profiles = profile_ids - {GROK_PROFILE, GEMINI_PROFILE}
    if unexpected_profiles:
        raise InstallError(
            "CLIProxyAPI managed block contains unexpected profiles: "
            + ", ".join(sorted(str(value) for value in unexpected_profiles))
        )
    return provider_id in provider_ids


def _provider_block(provider: Provider, include_provider: bool) -> str:
    lines = [BEGIN]
    if include_provider:
        lines += [
            f"[model_providers.{provider.provider_id}]",
            f"name = {json.dumps(provider.name)}",
            f"base_url = {json.dumps(provider.base_url)}",
            'wire_api = "responses"',
            "requires_openai_auth = false",
        ]
        if provider.env_key:
            lines.append(f"env_key = {json.dumps(provider.env_key)}")
    lines.append(END)
    return "\n".join(lines) + "\n"


def _insert_top_level_block(text: str, block: str) -> str:
    lines = text.splitlines()
    index = _first_table(lines)
    insertion = block.rstrip().splitlines()
    if index and lines[index - 1].strip():
        insertion.insert(0, "")
    if index < len(lines) and insertion and insertion[-1].strip():
        insertion.append("")
    lines[index:index] = insertion
    return "\n".join(lines).rstrip() + "\n"


def _legacy_profile_error(parsed: Mapping[str, object], source: str) -> None:
    if "profile" in parsed:
        raise InstallError(
            f"{source} contains an unmanaged legacy top-level `profile` selector; "
            "Codex 0.134.0+ requires a separate `<name>.config.toml` overlay. "
            "Move that configuration manually before rerunning setup."
        )
    profiles = parsed.get("profiles")
    if profiles is not None:
        names = (
            ", ".join(sorted(str(name) for name in profiles))
            if isinstance(profiles, Mapping)
            else "an invalid profiles value"
        )
        raise InstallError(
            f"{source} contains unmanaged legacy `[profiles.*]` configuration ({names}); "
            "move each profile to a separate `<name>.config.toml` file before rerunning setup."
        )


def render_base_config(
    original: str,
    provider: Provider,
    activate_provider: bool,
    default_model: str | None,
) -> str:
    parsed_original = parse_toml(original, "existing config.toml")
    base, managed = _managed_region(
        original,
        BEGIN,
        END,
        "CLIProxyAPI base configuration",
    )
    managed_provider = _validate_legacy_block(managed, provider.provider_id)
    parsed_base = parse_toml(base, "base configuration outside the managed block")

    legacy_selector = parsed_base.get("profile")
    if legacy_selector in {GROK_PROFILE, GEMINI_PROFILE}:
        base = _remove_top_level_key(base, "profile")
        parsed_base = parse_toml(base, "base configuration after legacy selector migration")
    _legacy_profile_error(parsed_base, "config.toml outside the CLIProxyAPI managed block")

    include_provider = provider.is_new or managed_provider
    if not include_provider and not has_table(
        base,
        f"model_providers.{provider.provider_id}",
    ):
        raise InstallError("selected existing provider table could not be located safely")

    top: dict[str, str] = {}
    if activate_provider:
        top["model_provider"] = provider.provider_id
    if default_model:
        top["model"] = default_model
    if top:
        base = upsert_top_level(base, top)

    block = _provider_block(provider, include_provider)
    rendered = base.rstrip() + ("\n\n" if base.strip() else "") + block
    parsed = parse_toml(rendered, "generated config.toml")
    _legacy_profile_error(parsed, "generated config.toml")
    if activate_provider and parsed.get("model_provider") != provider.provider_id:
        raise InstallError("generated config.toml did not activate CLIProxyAPI")
    providers = parsed.get("model_providers")
    if not isinstance(providers, Mapping) or not isinstance(
        providers.get(provider.provider_id),
        Mapping,
    ):
        raise InstallError("generated config.toml lost the CLIProxyAPI provider")
    if not include_provider:
        old_providers = parsed_original.get("model_providers", {})
        old_provider = (
            old_providers.get(provider.provider_id)
            if isinstance(old_providers, Mapping)
            else None
        )
        if old_provider != providers.get(provider.provider_id):
            raise InstallError("existing provider table changed unexpectedly")
    return rendered


def render_profile_config(
    original: str,
    profile_name: str,
    model: str,
    provider_id: str,
    instructions: str | None = None,
    catalog_path: Path | None = None,
) -> str:
    source = f"{profile_name}.config.toml"
    parse_toml(original, f"existing {source}")
    base, managed = _managed_region(
        original,
        PROFILE_BEGIN,
        PROFILE_END,
        f"{source}",
    )
    if managed is not None:
        managed_parsed = parse_toml(managed, f"existing managed block in {source}")
        unexpected = set(managed_parsed) - {"model", "model_provider", "developer_instructions", "model_catalog_json"}
        if unexpected:
            raise InstallError(
                f"managed block in {source} contains unexpected keys: "
                + ", ".join(sorted(unexpected))
            )
    parsed_base = parse_toml(base, f"{source} outside the managed block")
    _legacy_profile_error(parsed_base, source)
    collisions = sorted(
        key for key in ("model", "model_provider", "developer_instructions", "model_instructions_file", "model_catalog_json") if key in parsed_base and (instructions is not None or key in {"model", "model_provider"})
    )
    if collisions:
        raise InstallError(
            f"{source} already defines unmanaged {', '.join(collisions)}; "
            "refusing to replace user-owned profile settings. Move or remove those keys first."
        )
    block = "\n".join(
        [
            PROFILE_BEGIN,
            f"model = {json.dumps(model, ensure_ascii=False)}",
            f"model_provider = {json.dumps(provider_id, ensure_ascii=False)}",
            *([f"developer_instructions = {json.dumps(instructions, ensure_ascii=False)}"] if instructions is not None else []),
            *([f"model_catalog_json = {json.dumps(str(catalog_path), ensure_ascii=False)}"] if catalog_path is not None else []),
            PROFILE_END,
        ]
    ) + "\n"
    rendered = _insert_top_level_block(base, block)
    parsed = parse_toml(rendered, f"generated {source}")
    if parsed.get("model") != model or parsed.get("model_provider") != provider_id:
        raise InstallError(f"generated {source} failed top-level overlay validation")
    _legacy_profile_error(parsed, f"generated {source}")
    return rendered


def render_documents(
    *,
    base_original: str,
    grok_original: str,
    gemini_original: str,
    luna_original: str = "",
    luna_grok_original: str = "",
    grok_gemini_original: str = "",
    catalog_path: Path,
    provider: Provider,
    models: Models,
    activate_provider: bool,
    default_model: str | None,
) -> ConfigDocuments:
    documents = ConfigDocuments(
        luna=render_profile_config(luna_original, LUNA_PROFILE, models.luna, provider.provider_id),
        luna_grok=render_profile_config(luna_grok_original, "luna-grok", models.luna,
                                       provider.provider_id, council_instructions("luna-grok"), catalog_path),
        grok_gemini=render_profile_config(grok_gemini_original, "grok-gemini", models.grok,
                                         provider.provider_id, council_instructions("grok-gemini"), catalog_path),
        base=render_base_config(
            base_original,
            provider,
            activate_provider,
            default_model,
        ),
        grok=render_profile_config(
            grok_original,
            GROK_PROFILE,
            models.grok,
            provider.provider_id,
        ),
        gemini=render_profile_config(
            gemini_original,
            GEMINI_PROFILE,
            models.gemini,
            provider.provider_id,
        ),
    )
    validate_documents(documents, provider, models, activate_provider, catalog_path)
    return documents


def validate_documents(
    documents: ConfigDocuments,
    provider: Provider,
    models: Models,
    activate_provider: bool,
    catalog_path: Path,
) -> None:
    base = parse_toml(documents.base, "base config.toml")
    validate_council_installation(models)
    _legacy_profile_error(base, "base config.toml")
    providers = base.get("model_providers")
    if not isinstance(providers, Mapping):
        raise InstallError("base config.toml has no model_providers table")
    configured_provider = providers.get(provider.provider_id)
    if not isinstance(configured_provider, Mapping):
        raise InstallError(
            f"base config.toml has no provider {provider.provider_id!r}"
        )
    if activate_provider and base.get("model_provider") != provider.provider_id:
        raise InstallError("base config.toml does not select the CLIProxyAPI provider")

    expected = (
        (GROK_PROFILE, documents.grok, models.grok),
        (GEMINI_PROFILE, documents.gemini, models.gemini),
        (LUNA_PROFILE, documents.luna, models.luna),
        ("luna-grok", documents.luna_grok, models.luna),
        ("grok-gemini", documents.grok_gemini, models.grok),
    )
    for name, text, model in expected:
        parsed = parse_toml(text, f"{name}.config.toml")
        _legacy_profile_error(parsed, f"{name}.config.toml")
        if parsed.get("model") != model:
            raise InstallError(f"{name}.config.toml selects the wrong model")
        if parsed.get("model_provider") != provider.provider_id:
            raise InstallError(f"{name}.config.toml selects the wrong provider")
        if name in COUNCILS:
            if not catalog_path.is_absolute() or parsed.get("model_catalog_json") != str(catalog_path):
                raise InstallError(f"{name}.config.toml has incorrect managed model catalog pointer")
            if "model_instructions_file" in parsed:
                raise InstallError(f"{name}.config.toml overrides model instructions")
            if parsed.get("developer_instructions") != council_instructions(name):
                raise InstallError(f"{name}.config.toml has incorrect council instructions")
            if parsed.get("model") != COUNCILS[name][0]:
                raise InstallError(f"{name} requires exact leader {COUNCILS[name][0]}")

