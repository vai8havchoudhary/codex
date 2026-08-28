"""Comment-preserving Codex TOML rendering and atomic writes."""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Mapping

from catalog import (
    BEGIN, END, GEMINI_PROFILE, GROK_PROFILE, KEY_RE, TABLE_RE,
    InstallError, Models, Provider, parse_toml,
)

def strip_managed_block(text: str) -> str:
    if BEGIN not in text and END not in text:
        return text
    if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) > text.index(END):
        raise InstallError("malformed CLIProxyAPI managed block in config.toml")
    start = text.index(BEGIN)
    finish = text.index(END) + len(END)
    return (text[:start].rstrip() + "\n" + text[finish:].lstrip("\n")).rstrip() + "\n"


def split_comment(value: str) -> tuple[str, str]:
    basic = literal = escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
        elif char == "\\" and basic:
            escaped = True
        elif char == '"' and not literal:
            basic = not basic
        elif char == "'" and not basic:
            literal = not literal
        elif char == "#" and not basic and not literal:
            return value[:index].rstrip(), value[index:].rstrip()
    return value.rstrip(), ""


def upsert_top_level(text: str, values: Mapping[str, str]) -> str:
    lines = text.splitlines()
    first_table = next((index for index, line in enumerate(lines) if TABLE_RE.match(line)), len(lines))
    rows: dict[str, int] = {}
    for index in range(first_table):
        match = KEY_RE.match(lines[index])
        if match:
            rows[match.group("key")] = index
    inserts: list[str] = []
    for key, value in values.items():
        encoded = json.dumps(value, ensure_ascii=False)
        if key not in rows:
            inserts.append(f"{key} = {encoded}")
            continue
        index = rows[key]
        match = KEY_RE.match(lines[index])
        assert match is not None
        _, comment = split_comment(match.group("value"))
        suffix = f" {comment}" if comment else ""
        lines[index] = f"{match.group('indent')}{key}{match.group('pre')}={match.group('post')}{encoded}{suffix}"
    if inserts:
        if first_table and lines[first_table - 1].strip():
            inserts.append("")
        lines[first_table:first_table] = inserts
    return "\n".join(lines).rstrip() + "\n"


def has_table(text: str, path: str) -> bool:
    return any(match and match.group(1) == "[" and match.group(2).strip().strip('"') == path for line in text.splitlines() if (match := TABLE_RE.match(line)))


def managed_block(provider: Provider, models: Models, include_provider: bool) -> str:
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
        lines.append("")
    lines += [
        f"[profiles.{GROK_PROFILE}]",
        f"model = {json.dumps(models.grok)}",
        f"model_provider = {json.dumps(provider.provider_id)}",
        "",
        f"[profiles.{GEMINI_PROFILE}]",
        f"model = {json.dumps(models.gemini)}",
        f"model_provider = {json.dumps(provider.provider_id)}",
        END,
    ]
    return "\n".join(lines) + "\n"


def render_config(
    original: str,
    provider: Provider,
    models: Models,
    activate_provider: bool,
    default_model: str | None,
) -> str:
    parsed_original = parse_toml(original, "existing configuration")
    base = strip_managed_block(original)
    managed_provider = BEGIN in original and END in original
    include_provider = provider.is_new or managed_provider
    if not include_provider and not has_table(base, f"model_providers.{provider.provider_id}"):
        raise InstallError("selected existing provider table could not be located safely")
    for profile in (GROK_PROFILE, GEMINI_PROFILE):
        if has_table(base, f"profiles.{profile}"):
            raise InstallError(f"profile {profile!r} already exists outside the managed block")
    top: dict[str, str] = {}
    if activate_provider:
        top["model_provider"] = provider.provider_id
    if default_model:
        top["model"] = default_model
    if top:
        base = upsert_top_level(base, top)
    block = managed_block(provider, models, include_provider)
    rendered = base.rstrip() + ("\n\n" if base.strip() else "") + block
    parsed = parse_toml(rendered, "generated configuration")
    if activate_provider and parsed.get("model_provider") != provider.provider_id:
        raise InstallError("generated configuration did not activate CLIProxyAPI")
    profiles = parsed.get("profiles")
    if not isinstance(profiles, Mapping):
        raise InstallError("generated configuration lost profiles")
    expected = {GROK_PROFILE: models.grok, GEMINI_PROFILE: models.gemini}
    for name, model in expected.items():
        profile = profiles.get(name)
        if not isinstance(profile, Mapping) or profile.get("model") != model or profile.get("model_provider") != provider.provider_id:
            raise InstallError(f"generated profile {name!r} failed validation")
    if not include_provider and parsed_original.get("model_providers", {}).get(provider.provider_id) != parsed.get("model_providers", {}).get(provider.provider_id):
        raise InstallError("existing provider table changed unexpectedly")
    return rendered


def atomic_write(path: Path, content: str) -> Path | None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup: Path | None = None
    if path.exists():
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = path.with_name(f"{path.name}.bak.{stamp}")
        counter = 1
        while backup.exists():
            backup = path.with_name(f"{path.name}.bak.{stamp}.{counter}")
            counter += 1
        shutil.copy2(path, backup)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        os.chmod(temp_path, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return backup


