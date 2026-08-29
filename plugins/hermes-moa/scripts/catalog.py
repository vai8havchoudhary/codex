"""Secret-safe CLIProxyAPI catalog discovery and exact model admission."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

CLIENT_VERSION = "999.0.0"
KEY_ENV = "CLIPROXY_API_KEY"
DEFAULT_URL = "http://127.0.0.1:8317"
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


class CatalogError(RuntimeError):
    """A fail-closed catalog or endpoint admission error."""


@dataclass(frozen=True)
class Catalogs:
    openai_ids: tuple[str, ...]
    codex_slugs: tuple[str, ...]


@dataclass(frozen=True)
class Models:
    grok: str
    gemini: str


def normalize_base_url(raw: str) -> str:
    """Return an OpenAI-compatible base URL with exactly one ``/v1`` suffix."""
    value = raw.strip().rstrip("/")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise CatalogError("CLIPROXY_URL must be an absolute http:// or https:// URL")
    if parsed.username or parsed.password:
        raise CatalogError("CLIPROXY_URL must not embed credentials")
    if parsed.query or parsed.fragment:
        raise CatalogError("CLIPROXY_URL must not contain a query string or fragment")
    path = parsed.path.rstrip("/")
    if path not in {"", "/v1"}:
        raise CatalogError("CLIPROXY_URL path must be empty or /v1")
    if parsed.scheme == "http" and parsed.hostname.lower() not in LOOPBACK_HOSTS:
        raise CatalogError(
            "plain HTTP is allowed only for localhost or loopback CLIProxyAPI endpoints"
        )
    origin = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    return f"{origin}/v1"


def models_url(base_url: str, *, codex: bool) -> str:
    base = normalize_base_url(base_url)
    path = f"{base}/models"
    if not codex:
        return path
    return f"{path}?{urllib.parse.urlencode({'client_version': CLIENT_VERSION})}"


def _request_json(url: str, api_key: str, timeout: float) -> Any:
    if not api_key:
        raise CatalogError(f"{KEY_ENV} is not set")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "codex-hermes-moa/1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise CatalogError(f"CLIProxyAPI returned HTTP {exc.code} for {url}") from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"unable to read CLIProxyAPI catalog at {url}: {exc}") from exc


def _load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"cannot read {label} {path}: {exc}") from exc


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))


def extract_openai_ids(payload: Any) -> tuple[str, ...]:
    entries = (
        payload.get("data")
        if isinstance(payload, Mapping)
        else payload
        if isinstance(payload, list)
        else None
    )
    if not isinstance(entries, list):
        raise CatalogError("/v1/models response must contain a JSON `data` list")
    values: list[str] = []
    for entry in entries:
        raw = entry if isinstance(entry, str) else entry.get("id") if isinstance(entry, Mapping) else None
        if isinstance(raw, str):
            values.append(raw)
    result = _unique(values)
    if not result:
        raise CatalogError("/v1/models returned no model IDs")
    return result


def extract_codex_slugs(payload: Any) -> tuple[str, ...]:
    entries = payload.get("models") if isinstance(payload, Mapping) else None
    if not isinstance(entries, list):
        raise CatalogError("CLIProxyAPI did not return a Codex-compatible `models` catalog")
    values = [entry.get("slug", "") for entry in entries if isinstance(entry, Mapping)]
    result = _unique([value for value in values if isinstance(value, str)])
    if not result:
        raise CatalogError("CLIProxyAPI Codex catalog returned no model slugs")
    return result


def read_catalogs(
    base_url: str,
    api_key: str,
    *,
    models_file: Path | None = None,
    codex_models_file: Path | None = None,
    timeout: float = 5.0,
) -> Catalogs:
    base = normalize_base_url(base_url)
    if models_file is not None:
        if codex_models_file is None:
            raise CatalogError(
                "offline verification also requires --codex-models-response-file"
            )
        openai_payload = _load_json(models_file, "OpenAI model response file")
        codex_payload = _load_json(codex_models_file, "Codex model response file")
    elif codex_models_file is not None:
        raise CatalogError(
            "--codex-models-response-file requires --models-response-file"
        )
    else:
        openai_payload = _request_json(models_url(base, codex=False), api_key, timeout)
        codex_payload = _request_json(models_url(base, codex=True), api_key, timeout)
    return Catalogs(
        openai_ids=extract_openai_ids(openai_payload),
        codex_slugs=extract_codex_slugs(codex_payload),
    )


def _canon(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _family_match(model_id: str, family: str, version: str, marker: str | None) -> bool:
    tokens = _canon(model_id).split("-")
    wanted = _canon(version).split("-")
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


def _stable_alias(model_id: str, suffixes: Sequence[str]) -> bool:
    value = _canon(model_id)
    if any(value == suffix or value.endswith(f"-{suffix}") for suffix in suffixes):
        return True
    qualifier = value.rsplit("-", 1)[-1]
    if qualifier in {"latest", "preview", "beta"} or (
        qualifier.isdigit() and len(qualifier) >= 6
    ):
        stem = value[: -(len(qualifier) + 1)]
        return any(stem == suffix or stem.endswith(f"-{suffix}") for suffix in suffixes)
    return False


def _resolve_one(
    catalogs: Catalogs,
    *,
    family: str,
    version: str,
    marker: str | None,
    explicit: str | None,
) -> str:
    common = tuple(value for value in catalogs.openai_ids if value in catalogs.codex_slugs)
    label = f"{family} {version}" + (f" {marker}" if marker else "")
    if explicit:
        if explicit not in common:
            raise CatalogError(
                f"requested alias {explicit!r} is not present in both CLIProxyAPI catalogs"
            )
        if not _family_match(explicit, family, version, marker):
            raise CatalogError(f"requested alias {explicit!r} is not an exact {label} model")
        return explicit

    candidates = [
        value
        for value in common
        if _family_match(value, family, version, marker)
    ]
    version_suffix = _canon(version)
    suffixes = [f"{family}-{version_suffix}"]
    if marker:
        suffixes = [
            f"{family}-{version_suffix}-{marker}",
            f"{family}-{marker}-{version_suffix}",
        ]
    preferred = [value for value in candidates if _stable_alias(value, suffixes)]
    pool = preferred or candidates
    if len(pool) == 1:
        return pool[0]
    if not pool:
        raise CatalogError(
            f"CLIProxyAPI does not export an exact {label} alias in both catalogs"
        )
    raise CatalogError(
        f"CLIProxyAPI exports multiple possible aliases for {label}: "
        f"{', '.join(pool)}; select one explicitly"
    )


def resolve_models(
    catalogs: Catalogs,
    *,
    grok: str | None = None,
    gemini: str | None = None,
) -> Models:
    return Models(
        grok=_resolve_one(
            catalogs,
            family="grok",
            version="4.6",
            marker=None,
            explicit=grok,
        ),
        gemini=_resolve_one(
            catalogs,
            family="gemini",
            version="3.7",
            marker="flash",
            explicit=gemini,
        ),
    )


def environment_key() -> str:
    """Return the configured API key without logging or persisting it."""
    return os.environ.get(KEY_ENV, "")
