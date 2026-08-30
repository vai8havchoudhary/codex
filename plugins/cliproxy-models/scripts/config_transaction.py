"""Three-file permission-restricted Codex configuration transactions."""
from __future__ import annotations

import datetime as dt
import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from catalog import InstallError

REQUIRED_MODE = 0o600


@dataclass(frozen=True)
class FileState:
    path: Path
    existed: bool
    content: str
    mode: int | None


@dataclass(frozen=True)
class PlannedFile:
    state: FileState
    rendered: str

    @property
    def changed(self) -> bool:
        return (
            not self.state.existed
            or self.state.content != self.rendered
            or self.state.mode != REQUIRED_MODE
        )


def read_state(path: Path, label: str) -> FileState:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return FileState(path, False, "", None)
    except OSError as exc:
        raise InstallError(f"cannot inspect {label} at {path}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode):
        raise InstallError(f"refusing symlink {label} at {path}")
    if not stat.S_ISREG(info.st_mode):
        raise InstallError(f"{label} at {path} must be a regular file")
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise InstallError(f"cannot read UTF-8 {label} at {path}: {exc}") from exc
    return FileState(path, True, content, stat.S_IMODE(info.st_mode))


def _assert_unchanged(state: FileState) -> None:
    current = read_state(state.path, str(state.path))
    if (
        current.existed != state.existed
        or current.content != state.content
        or current.mode != state.mode
    ):
        raise InstallError(
            f"configuration changed concurrently at {state.path}; refusing partial update"
        )


def _fsync_directory(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _replace_text(path: Path, content: str, mode: int) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temp_path = Path(temp_name)
    try:
        os.chmod(temp_path, mode)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.is_symlink():
            raise InstallError(f"refusing to replace symlink at {path}")
        os.replace(temp_path, path)
        os.chmod(path, mode)
        _fsync_directory(path.parent)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _backup_path(path: Path, stamp: str) -> Path:
    backup = path.with_name(f"{path.name}.bak.{stamp}")
    counter = 1
    while backup.exists() or backup.is_symlink():
        backup = path.with_name(f"{path.name}.bak.{stamp}.{counter}")
        counter += 1
    return backup


def _remove_regular(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or not path.is_file():
        raise InstallError(f"refusing to remove unsafe transaction path {path}")
    path.unlink()
    _fsync_directory(path.parent)


def transactional_write(
    plans: Sequence[PlannedFile],
    post_validate: Callable[[], None],
) -> dict[Path, Path]:
    paths = [plan.state.path for plan in plans]
    if len(set(paths)) != len(paths):
        raise InstallError("configuration transaction contains duplicate paths")
    changed = [plan for plan in plans if plan.changed]
    if not changed:
        return {}

    for plan in changed:
        _assert_unchanged(plan.state)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backups: dict[Path, Path] = {}
    try:
        for plan in changed:
            state = plan.state
            if not state.existed:
                continue
            backup = _backup_path(state.path, stamp)
            _replace_text(backup, state.content, REQUIRED_MODE)
            backups[state.path] = backup
        for plan in changed:
            _replace_text(plan.state.path, plan.rendered, REQUIRED_MODE)
        post_validate()
        for plan in plans:
            current = read_state(plan.state.path, str(plan.state.path))
            if not current.existed or current.content != plan.rendered:
                raise InstallError(
                    f"post-write validation found unexpected bytes at {plan.state.path}"
                )
            if current.mode != REQUIRED_MODE:
                raise InstallError(
                    f"post-write validation found unsafe mode at {plan.state.path}"
                )
        return backups
    except Exception as exc:
        rollback_errors: list[str] = []
        for plan in reversed(changed):
            state = plan.state
            try:
                if state.existed:
                    _replace_text(
                        state.path,
                        state.content,
                        state.mode if state.mode is not None else REQUIRED_MODE,
                    )
                else:
                    _remove_regular(state.path)
            except Exception as rollback_exc:  # pragma: no cover - catastrophic path
                rollback_errors.append(f"{state.path}: {rollback_exc}")
        for backup in backups.values():
            try:
                _remove_regular(backup)
            except Exception as cleanup_exc:  # pragma: no cover - catastrophic path
                rollback_errors.append(f"{backup}: {cleanup_exc}")
        detail = f"configuration transaction failed and was rolled back: {exc}"
        if rollback_errors:
            detail += "; rollback errors: " + "; ".join(rollback_errors)
        raise InstallError(detail) from exc


# Backward-compatible single-file helper retained for third-party callers. The
# installer itself always uses transactional_write for the base and both overlays.
def atomic_write(path: Path, content: str) -> Path | None:
    state = read_state(path, str(path))
    plan = PlannedFile(state, content)
    backups = transactional_write([plan], lambda: None)
    return backups.get(path)
