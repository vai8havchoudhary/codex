"""CLIProxyAPI catalog, exact-alias, and provider admission contracts."""
from __future__ import annotations

import json
import os
import re
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_CONFIG = Path.home() / ".codex" / "config.toml"
DEFAULT_PROVIDER_ID = "cliproxyapi"
DEFAULT_BASE_URL = "http://127.0.0.1:8317/v1"
DEFAULT_KEY_ENV = "CLIPROXY_API_KEY"
GROK_PROFILE = "cliproxy-grok-4-6"
GEMINI_PROFILE = "cliproxy-gemini-3-7-flash"
BEGIN = "# BEGIN CODEX CLIPROXYAPI MODELS (managed)"
END = "# END CODEX CLIPROXYAPI MODELS (managed)"
CLIENT_VERSION = "999.0.0"
TABLE_RE = re.compile(r"^\s*(\[\[|\[)([^\]]+)(\]\]|\])\s*(?:#.*)?$")
KEY_RE = re.compile(r"^(?P<indent>\s*)(?P<key>[A-Za-z0-9_-]+)(?P<pre>\s*)=(?P<post>\s*)(?P<value>.*)$")

class InstallError(RuntimeError):
    """Fail-closed installation error with an actionable message."""


@dataclass(frozen=True)
class Provider:
    provider_id: str
    name: str
    base_url: str
    env_key: str | None
    is_new: bool


@dataclass(frozen=True)
class Catalogs:
    openai_ids: tuple[str, ...]
    codex_slugs: tuple[str, ...]


@dataclass(frozen=True)
class Models:
    grok: str
    gemini: str


def parse_toml(text: str, source: str) -> dict[str, Any]:
    try:
        value = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise InstallError(f"refusing to edit invalid TOML in {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise InstallError(f"unexpected TOML document in {source}")
    return value


def normalize_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise InstallError("CLIProxyAPI base URL must be an absolute http:// or https:// URL")
    if parsed.query or parsed.fragment:
        raise InstallError("CLIProxyAPI base URL must not contain a query string or fragment")
    return value


def models_url(base_url: str, codex: bool) -> str:
    base = normalize_base_url(base_url)
    path = f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"
    if not codex:
        return path
    return f"{path}?{urllib.parse.urlencode({'client_version': CLIENT_VERSION})}"


def request_json(url: str, env_key: str | None, timeout: float) -> Any:
    headers = {"Accept": "application/json", "User-Agent": "codex-cliproxyapi-installer/1"}
    if env_key:
        token = os.environ.get(env_key)
        if not token:
            raise InstallError(f"provider uses environment variable {env_key!r}, but it is unset")
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        hint = " Pass --api-key-env NAME." if exc.code in (401, 403) and not env_key else ""
        raise InstallError(f"CLIProxyAPI returned HTTP {exc.code} for {url}.{hint}") from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise InstallError(f"unable to read CLIProxyAPI catalog at {url}: {exc}") from exc


def load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallError(f"cannot read {label} {path}: {exc}") from exc


def unique_strings(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))


def extract_openai_ids(payload: Any) -> tuple[str, ...]:
    entries = payload.get("data") if isinstance(payload, Mapping) else payload if isinstance(payload, list) else None
    if not isinstance(entries, list):
        raise InstallError("/v1/models response must contain a JSON `data` list")
    values: list[str] = []
    for entry in entries:
        raw = entry if isinstance(entry, str) else entry.get("id") if isinstance(entry, Mapping) else None
        if isinstance(raw, str):
            values.append(raw)
    result = unique_strings(values)
    if not result:
        raise InstallError("/v1/models returned no model IDs")
    return result


def extract_codex_slugs(payload: Any) -> tuple[str, ...]:
    entries = payload.get("models") if isinstance(payload, Mapping) else None
    if not isinstance(entries, list):
        raise InstallError("CLIProxyAPI did not return a Codex-compatible `models` catalog")
    values = [entry.get("slug", "") for entry in entries if isinstance(entry, Mapping)]
    result = unique_strings([value for value in values if isinstance(value, str)])
    if not result:
        raise InstallError("CLIProxyAPI Codex catalog returned no model slugs")
    return result


def read_catalogs(
    base_url: str,
    env_key: str | None,
    models_file: Path | None,
    codex_models_file: Path | None,
    timeout: float,
) -> Catalogs:
    if models_file:
        openai_payload = load_json(models_file, "model response file")
        if not codex_models_file:
            raise InstallError("offline verification also requires --codex-models-response-file")
        codex_payload = load_json(codex_models_file, "Codex model response file")
    elif codex_models_file:
        raise InstallError("--codex-models-response-file requires --models-response-file")
    else:
        openai_payload = request_json(models_url(base_url, False), env_key, timeout)
        codex_payload = request_json(models_url(base_url, True), env_key, timeout)
    return Catalogs(extract_openai_ids(openai_payload), extract_codex_slugs(codex_payload))


def canon(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def family_match(model_id: str, family: str, version: str, marker: str | None) -> bool:
    tokens = canon(model_id).split("-")
    wanted = canon(version).split("-")
    for index, token in enumerate(tokens):
        if token != family:
            continue
        tail = tokens[index + 1 :]
        for start in range(len(tail) - len(wanted) + 1):
            if tail[start : start + len(wanted)] != wanted:
                continue
            after = tail[start + len(wanted) :]
            if after and after[0].isdigit() and len(after[0]) <= 2:
                continue
            if marker is None or marker in tokens:
                return True
    return False


def stable_alias(model_id: str, suffixes: Sequence[str]) -> bool:
    value = canon(model_id)
    if any(value == suffix or value.endswith(f"-{suffix}") for suffix in suffixes):
        return True
    qualifier = value.rsplit("-", 1)[-1]
    if qualifier in {"latest", "preview", "beta"} or (qualifier.isdigit() and len(qualifier) >= 6):
        stem = value[: -(len(qualifier) + 1)]
        return any(stem == suffix or stem.endswith(f"-{suffix}") for suffix in suffixes)
    return False


def resolve_one(
    catalogs: Catalogs,
    family: str,
    version: str,
    marker: str | None,
    explicit: str | None,
) -> str:
    common = tuple(value for value in catalogs.openai_ids if value in catalogs.codex_slugs)
    label = f"{family} {version}" + (f" {marker}" if marker else "")
    if explicit:
        if explicit not in common:
            raise InstallError(f"requested alias {explicit!r} is not present in both CLIProxyAPI catalogs")
        if not family_match(explicit, family, version, marker):
            raise InstallError(f"requested alias {explicit!r} is not an exact {label} model")
        return explicit
    candidates = [value for value in common if family_match(value, family, version, marker)]
    version_suffix = canon(version)
    suffixes = [f"{family}-{version_suffix}"]
    if marker:
        suffixes = [f"{family}-{version_suffix}-{marker}", f"{family}-{marker}-{version_suffix}"]
    preferred = [value for value in candidates if stable_alias(value, suffixes)]
    pool = preferred or candidates
    if len(pool) == 1:
        return pool[0]
    if not pool:
        raise InstallError(f"CLIProxyAPI does not export an exact {label} alias in both catalogs")
    raise InstallError(f"CLIProxyAPI exports multiple possible aliases for {label}: {', '.join(pool)}; select one explicitly")


def resolve_models(catalogs: Catalogs, grok: str | None = None, gemini: str | None = None) -> Models:
    return Models(
        resolve_one(catalogs, "grok", "4.6", None, grok),
        resolve_one(catalogs, "gemini", "3.7", "flash", gemini),
    )


def provider_tables(parsed: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = parsed.get("model_providers", {})
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise InstallError("`model_providers` must be a TOML table")
    return {str(key): value for key, value in raw.items() if isinstance(value, Mapping)}


def looks_like_cliproxy(provider_id: str, table: Mapping[str, Any]) -> bool:
    text = " ".join(str(value) for value in (provider_id, table.get("name", ""), table.get("base_url", ""))).lower()
    return "cliproxy" in text or ":8317" in text


def choose_provider(parsed: Mapping[str, Any], requested_id: str, base_url: str, env_key: str | None) -> Provider:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", requested_id):
        raise InstallError("provider ID may contain only letters, digits, underscores, and hyphens")
    requested_base = normalize_base_url(base_url)
    tables = provider_tables(parsed)
    likely = [(key, value) for key, value in tables.items() if looks_like_cliproxy(key, value)]
    if requested_id in tables:
        provider_id, table = requested_id, tables[requested_id]
        existing_base = table.get("base_url")
        same_endpoint = isinstance(existing_base, str) and normalize_base_url(existing_base) == requested_base
        table_text = " ".join(str(value) for value in (table.get("name", ""), table.get("base_url", ""))).lower()
        table_is_cliproxy = "cliproxy" in table_text or ":8317" in table_text
        if not table_is_cliproxy and not same_endpoint:
            raise InstallError(f"provider ID {requested_id!r} belongs to an unrelated provider")
    elif len(likely) == 1:
        provider_id, table = likely[0]
    elif len(likely) > 1:
        raise InstallError("multiple CLIProxyAPI-like providers exist; select one with --provider-id")
    else:
        provider_id, table = requested_id, {}
    existing_base = table.get("base_url")
    selected_base = normalize_base_url(existing_base) if isinstance(existing_base, str) and existing_base.strip() else requested_base
    existing_env = table.get("env_key")
    selected_env = existing_env.strip() if isinstance(existing_env, str) and existing_env.strip() else env_key
    if isinstance(existing_env, str) and existing_env.strip() and env_key and existing_env.strip() != env_key:
        raise InstallError(f"existing provider uses env_key {existing_env!r}; refusing to replace it")
    name = table.get("name")
    selected_name = name.strip() if isinstance(name, str) and name.strip() else "CLIProxyAPI"
    return Provider(provider_id, selected_name, selected_base, selected_env, provider_id not in tables)


