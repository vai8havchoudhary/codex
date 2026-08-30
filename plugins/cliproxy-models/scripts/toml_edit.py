"""Comment-preserving low-level TOML text edits for Codex configuration."""
from __future__ import annotations

import json
from typing import Mapping, Sequence

from catalog import BEGIN, END, KEY_RE, TABLE_RE, InstallError

PROFILE_BEGIN = "# BEGIN CODEX CLIPROXYAPI PROFILE (managed)"
PROFILE_END = "# END CODEX CLIPROXYAPI PROFILE (managed)"


def _managed_region(
    text: str,
    begin: str,
    end: str,
    label: str,
) -> tuple[str, str | None]:
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if line.strip() == begin]
    finishes = [index for index, line in enumerate(lines) if line.strip() == end]
    if not starts and not finishes:
        return text, None
    if len(starts) != 1 or len(finishes) != 1 or starts[0] >= finishes[0]:
        raise InstallError(f"malformed {label} managed block")
    start, finish = starts[0], finishes[0]
    managed = "\n".join(lines[start : finish + 1]) + "\n"
    remaining = lines[:start] + lines[finish + 1 :]
    while remaining and not remaining[-1].strip():
        remaining.pop()
    base = "\n".join(remaining)
    if base:
        base += "\n"
    return base, managed


def strip_managed_block(text: str) -> str:
    """Compatibility wrapper for callers and regression tests."""
    return _managed_region(text, BEGIN, END, "CLIProxyAPI base configuration")[0]


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


def _first_table(lines: Sequence[str]) -> int:
    return next(
        (index for index, line in enumerate(lines) if TABLE_RE.match(line)),
        len(lines),
    )


def _top_level_rows(lines: Sequence[str]) -> dict[str, int]:
    rows: dict[str, int] = {}
    for index in range(_first_table(lines)):
        match = KEY_RE.match(lines[index])
        if match:
            rows[match.group("key")] = index
    return rows


def upsert_top_level(text: str, values: Mapping[str, str]) -> str:
    lines = text.splitlines()
    first_table = _first_table(lines)
    rows = _top_level_rows(lines)
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
        lines[index] = (
            f"{match.group('indent')}{key}{match.group('pre')}="
            f"{match.group('post')}{encoded}{suffix}"
        )
    if inserts:
        if first_table and lines[first_table - 1].strip():
            inserts.append("")
        lines[first_table:first_table] = inserts
    return "\n".join(lines).rstrip() + "\n"


def _remove_top_level_key(text: str, key: str) -> str:
    lines = text.splitlines()
    rows = _top_level_rows(lines)
    if key not in rows:
        return text
    del lines[rows[key]]
    while lines and not lines[-1].strip():
        lines.pop()
    return ("\n".join(lines) + "\n") if lines else ""


def _table_paths(text: str) -> tuple[str, ...]:
    paths: list[str] = []
    for line in text.splitlines():
        match = TABLE_RE.match(line)
        if not match:
            continue
        paths.append(match.group(2).strip().strip('"'))
    return tuple(paths)


def has_table(text: str, path: str) -> bool:
    return path in _table_paths(text)

