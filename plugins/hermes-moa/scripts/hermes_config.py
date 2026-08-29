"""Transactional Hermes Agent MoA configuration over one CLIProxyAPI provider."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from catalog import Models

PROVIDER_ID = "cliproxy"
GROK_PRESET = "cliproxy-grok-led"
GEMINI_PRESET = "cliproxy-gemini-led"
KEY_ENV = "CLIPROXY_API_KEY"
_PROFILE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_MISSING = object()


class HermesError(RuntimeError):
    """A fail-closed Hermes discovery, admission, or mutation error."""


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class HermesTarget:
    executable: str
    home: Path
    profile: str | None = None

    @property
    def config_path(self) -> Path:
        root = self.home / "profiles" / self.profile if self.profile else self.home
        return root / "config.yaml"

    @property
    def prefix(self) -> list[str]:
        prefix = [self.executable]
        if self.profile:
            prefix += ["-p", self.profile]
        return prefix

    @property
    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["HERMES_HOME"] = str(self.home)
        if self.profile:
            env["HERMES_PROFILE"] = self.profile
        else:
            env.pop("HERMES_PROFILE", None)
        return env


@dataclass(frozen=True)
class SetupResult:
    config_path: Path
    changed: bool
    backup_path: Path | None
    active_preset: str
    grok_model: str
    gemini_model: str


def resolve_target(*, executable: str, home: Path | None, profile: str | None) -> HermesTarget:
    if profile and not _PROFILE_RE.fullmatch(profile):
        raise HermesError(
            "Hermes profile names may contain only letters, digits, dot, underscore, and hyphen"
        )
    candidate = executable.strip()
    if not candidate:
        raise HermesError("Hermes executable cannot be empty")
    resolved = shutil.which(candidate) if os.sep not in candidate else candidate
    if not resolved or not Path(resolved).is_file():
        raise HermesError(
            f"Hermes executable {candidate!r} was not found; install Hermes Agent first"
        )
    selected_home = home or Path(os.environ.get("HERMES_HOME", "~/.hermes"))
    return HermesTarget(
        executable=str(Path(resolved).resolve()),
        home=selected_home.expanduser().resolve(),
        profile=profile,
    )


def _redact(text: str, secrets: Iterable[str]) -> str:
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def run(
    target: HermesTarget,
    args: Sequence[str],
    *,
    check: bool = False,
    secrets: Iterable[str] = (),
) -> ProcessResult:
    completed = subprocess.run(
        [*target.prefix, *args],
        env=target.env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    result = ProcessResult(
        returncode=completed.returncode,
        stdout=_redact(completed.stdout, secrets),
        stderr=_redact(completed.stderr, secrets),
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Hermes error"
        raise HermesError(f"Hermes command failed ({' '.join(args)}): {detail}")
    return result


def ensure_moa_available(target: HermesTarget, *, secrets: Iterable[str] = ()) -> None:
    result = run(target, ["moa", "list"], secrets=secrets)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Hermes error"
        raise HermesError(
            "Hermes Agent does not expose a working `hermes moa` surface: " + detail
        )


def get_value(target: HermesTarget, key: str, *, secrets: Iterable[str] = ()) -> Any:
    result = run(target, ["config", "get", key, "--json"], secrets=secrets)
    if result.returncode != 0:
        return _MISSING
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise HermesError(f"Hermes returned non-JSON data for config key {key!r}") from exc


def _encode(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    return str(value)


def set_value(
    target: HermesTarget,
    key: str,
    value: Any,
    *,
    secrets: Iterable[str] = (),
) -> None:
    run(target, ["config", "set", key, _encode(value)], check=True, secrets=secrets)


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    return value


def _reference(model: str) -> list[dict[str, Any]]:
    return [{"provider": PROVIDER_ID, "model": model, "enabled": True}]


def _preset(
    *,
    reference_model: str,
    aggregator_model: str,
    reference_max_tokens: int,
    max_tokens: int,
    fanout: str,
) -> dict[str, Any]:
    return {
        "reference_models": _reference(reference_model),
        "aggregator": {"provider": PROVIDER_ID, "model": aggregator_model},
        "reference_max_tokens": reference_max_tokens,
        "max_tokens": max_tokens,
        "fanout": fanout,
        "enabled": True,
    }


def desired_values(
    *,
    base_url: str,
    models: Models,
    active_preset: str,
    activate: bool,
    privacy_filter: str,
    reference_max_tokens: int,
    max_tokens: int,
    fanout: str,
) -> dict[str, Any]:
    if active_preset not in {GROK_PRESET, GEMINI_PRESET}:
        raise HermesError(f"unsupported MoA preset {active_preset!r}")
    if privacy_filter not in {"display", "full"}:
        raise HermesError("privacy filter must be `display` or `full`")
    if fanout not in {"user_turn", "per_iteration"} and not re.fullmatch(
        r"every_n:[2-9][0-9]*", fanout
    ):
        raise HermesError(
            "fanout must be user_turn, per_iteration, or every_n:<N> with N >= 2"
        )
    if reference_max_tokens <= 0 or max_tokens <= 0:
        raise HermesError("token limits must be positive integers")

    values: dict[str, Any] = {
        f"providers.{PROVIDER_ID}": {
            "name": "CLIProxyAPI",
            "api": base_url,
            "key_env": KEY_ENV,
            "transport": "openai_chat",
        },
        f"moa.presets.{GROK_PRESET}": _preset(
            reference_model=models.gemini,
            aggregator_model=models.grok,
            reference_max_tokens=reference_max_tokens,
            max_tokens=max_tokens,
            fanout=fanout,
        ),
        f"moa.presets.{GEMINI_PRESET}": _preset(
            reference_model=models.grok,
            aggregator_model=models.gemini,
            reference_max_tokens=reference_max_tokens,
            max_tokens=max_tokens,
            fanout=fanout,
        ),
        "moa.privacy_filter": privacy_filter,
        "moa.default_preset": active_preset,
    }
    if activate:
        values["model.provider"] = "moa"
        values["model.default"] = active_preset
    return values


def activation_values(active_preset: str) -> dict[str, Any]:
    if active_preset not in {GROK_PRESET, GEMINI_PRESET}:
        raise HermesError(f"unsupported MoA preset {active_preset!r}")
    return {
        "moa.default_preset": active_preset,
        "model.provider": "moa",
        "model.default": active_preset,
    }


def _provider_owned(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and str(value.get("key_env") or "") == KEY_ENV
        and str(value.get("transport") or "") == "openai_chat"
    )


def _preset_owned(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    aggregator = value.get("aggregator")
    refs = value.get("reference_models")
    if isinstance(refs, str):
        try:
            refs = json.loads(refs)
        except json.JSONDecodeError:
            return False
    return (
        isinstance(aggregator, Mapping)
        and aggregator.get("provider") == PROVIDER_ID
        and isinstance(refs, list)
        and bool(refs)
        and all(
            isinstance(item, Mapping) and item.get("provider") == PROVIDER_ID
            for item in refs
        )
    )


def reconcile_value(key: str, current: Any, requested: Any, *, force: bool) -> Any:
    if current is _MISSING:
        return requested
    if key == f"providers.{PROVIDER_ID}":
        if _canonical(current) != _canonical(requested) and not _provider_owned(current) and not force:
            raise HermesError(
                f"refusing to overwrite foreign Hermes provider {PROVIDER_ID!r}; inspect it or rerun with --force"
            )
        return {**current, **requested} if isinstance(current, Mapping) else requested
    if key in {
        f"moa.presets.{GROK_PRESET}",
        f"moa.presets.{GEMINI_PRESET}",
    }:
        if _canonical(current) != _canonical(requested) and not _preset_owned(current) and not force:
            name = key.rsplit(".", 1)[-1]
            raise HermesError(
                f"refusing to overwrite foreign Hermes MoA preset {name!r}; inspect it or rerun with --force"
            )
        return {**current, **requested} if isinstance(current, Mapping) else requested
    return requested


def plan_changes(
    target: HermesTarget,
    values: Mapping[str, Any],
    *,
    force: bool,
    secrets: Iterable[str] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    final_values: dict[str, Any] = {}
    changes: dict[str, Any] = {}
    for key, requested in values.items():
        current = get_value(target, key, secrets=secrets)
        desired = reconcile_value(key, current, requested, force=force)
        final_values[key] = desired
        if current is _MISSING or _canonical(current) != _canonical(desired):
            changes[key] = desired
    return final_values, changes


def _contains(current: Any, desired: Any) -> bool:
    """Return whether a resolved Hermes value contains the managed value.

    Hermes may normalize presets by adding default fields. Managed mappings are
    therefore validated as exact requested subsets, while lists and scalars
    remain exact.
    """
    if isinstance(desired, Mapping):
        return isinstance(current, Mapping) and all(
            key in current and _contains(current[key], value)
            for key, value in desired.items()
        )
    if isinstance(desired, list):
        return _canonical(current) == _canonical(desired)
    return current == desired


def validate_values(
    target: HermesTarget,
    values: Mapping[str, Any],
    *,
    secrets: Iterable[str] = (),
) -> None:
    mismatches: list[str] = []
    for key, desired in values.items():
        current = get_value(target, key, secrets=secrets)
        if current is _MISSING or not _contains(current, desired):
            mismatches.append(key)
    if mismatches:
        raise HermesError("Hermes post-write validation failed for: " + ", ".join(mismatches))

def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        os.chmod(temp_path, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _backup_path(config_path: Path) -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = config_path.with_name(f"{config_path.name}.bak.cliproxy-moa.{stamp}")
    counter = 1
    while candidate.exists():
        candidate = config_path.with_name(
            f"{config_path.name}.bak.cliproxy-moa.{stamp}.{counter}"
        )
        counter += 1
    return candidate


def apply_setup(
    target: HermesTarget,
    values: Mapping[str, Any],
    *,
    force: bool,
    models: Models,
    active_preset: str,
    secrets: Iterable[str] = (),
) -> SetupResult:
    ensure_moa_available(target, secrets=secrets)
    config_path = target.config_path
    if config_path.is_symlink():
        raise HermesError(f"refusing to mutate symlinked Hermes config: {config_path}")
    original_exists = config_path.exists()
    original = config_path.read_bytes() if original_exists else b""
    final_values, changes = plan_changes(target, values, force=force, secrets=secrets)

    if not changes:
        return SetupResult(
            config_path=config_path,
            changed=False,
            backup_path=None,
            active_preset=active_preset,
            grok_model=models.grok,
            gemini_model=models.gemini,
        )

    try:
        for key, value in changes.items():
            set_value(target, key, value, secrets=secrets)
        validate_values(target, final_values, secrets=secrets)
        ensure_moa_available(target, secrets=secrets)
    except Exception as exc:
        try:
            if original_exists:
                _atomic_bytes(config_path, original)
            else:
                config_path.unlink(missing_ok=True)
        except Exception as rollback_exc:
            raise HermesError(
                f"Hermes setup failed and rollback also failed: {rollback_exc}"
            ) from exc
        if isinstance(exc, HermesError):
            raise
        raise HermesError(f"Hermes setup failed: {exc}") from exc

    final = config_path.read_bytes() if config_path.exists() else b""
    changed = final != original
    backup: Path | None = None
    if changed and original_exists:
        backup = _backup_path(config_path)
        _atomic_bytes(backup, original)

    return SetupResult(
        config_path=config_path,
        changed=changed,
        backup_path=backup,
        active_preset=active_preset,
        grok_model=models.grok,
        gemini_model=models.gemini,
    )


def _route_problems(name: str, value: Any, *, reference: str, aggregator: str) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    mismatched: list[str] = []
    if not isinstance(value, Mapping):
        return [name], []
    agg = value.get("aggregator")
    refs = value.get("reference_models")
    if isinstance(refs, str):
        try:
            refs = json.loads(refs)
        except json.JSONDecodeError:
            refs = None
    if not isinstance(agg, Mapping):
        missing.append(f"{name}.aggregator")
    elif agg.get("provider") != PROVIDER_ID or agg.get("model") != aggregator:
        mismatched.append(f"{name}.aggregator")
    expected_refs = _reference(reference)
    if refs is None:
        missing.append(f"{name}.reference_models")
    elif _canonical(refs) != _canonical(expected_refs):
        mismatched.append(f"{name}.reference_models")
    return missing, mismatched


def inspect_status(
    target: HermesTarget,
    *,
    base_url: str,
    models: Models,
    secrets: Iterable[str] = (),
) -> dict[str, Any]:
    ensure_moa_available(target, secrets=secrets)
    missing: list[str] = []
    mismatched: list[str] = []

    provider = get_value(target, f"providers.{PROVIDER_ID}", secrets=secrets)
    if not isinstance(provider, Mapping):
        missing.append(f"providers.{PROVIDER_ID}")
    else:
        expected_provider = {
            "api": base_url,
            "key_env": KEY_ENV,
            "transport": "openai_chat",
        }
        for field, desired in expected_provider.items():
            if field not in provider:
                missing.append(f"providers.{PROVIDER_ID}.{field}")
            elif provider.get(field) != desired:
                mismatched.append(f"providers.{PROVIDER_ID}.{field}")

    moa = get_value(target, "moa", secrets=secrets)
    presets = moa.get("presets") if isinstance(moa, Mapping) else None
    if not isinstance(presets, Mapping):
        missing.append("moa.presets")
        presets = {}
    grok = presets.get(GROK_PRESET, _MISSING)
    found_missing, found_mismatched = _route_problems(
        f"moa.presets.{GROK_PRESET}",
        grok,
        reference=models.gemini,
        aggregator=models.grok,
    )
    missing.extend(found_missing)
    mismatched.extend(found_mismatched)
    gemini = presets.get(GEMINI_PRESET, _MISSING)
    found_missing, found_mismatched = _route_problems(
        f"moa.presets.{GEMINI_PRESET}",
        gemini,
        reference=models.grok,
        aggregator=models.gemini,
    )
    missing.extend(found_missing)
    mismatched.extend(found_mismatched)

    default_preset = moa.get("default_preset") if isinstance(moa, Mapping) else None
    model = get_value(target, "model", secrets=secrets)
    main_provider = model.get("provider") if isinstance(model, Mapping) else None
    main_model = model.get("default") if isinstance(model, Mapping) else None
    return {
        "configured": not missing and not mismatched,
        "missing": missing,
        "mismatched": mismatched,
        "default_preset": default_preset,
        "active": main_provider == "moa" and main_model in {GROK_PRESET, GEMINI_PRESET},
        "active_preset": main_model if main_provider == "moa" else None,
        "config_path": str(target.config_path),
    }

