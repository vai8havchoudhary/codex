# Repository instructions

This repository is the `cliproxy` Codex marketplace with exactly two native plugins:

- `cliproxy-models`
- `codex-moa`

Read [agent.md](agent.md) before non-trivial changes.

## Non-negotiable invariants

- `release.json` is the bundle authority; manifests and `plugins/codex-moa/authority.json` must align exactly.
- The current contract is bundle `2.0.0`, `cliproxy-models` `1.1.0`, and `codex-moa` `2.0.0`.
- Keep exactly one Codex provider for CLIProxyAPI; never create providers per upstream account.
- Never read, enumerate, print, summarize, or persist proxy account files or the value of `CLIPROXY_API_KEY`.
- Persist only the environment-variable name `CLIPROXY_API_KEY`.
- Exact `gpt-5.6-luna` (never `-advisor`), `grok-4.6` and Gemini 3.7 Flash IDs must appear in both CLIProxyAPI catalogs. The current candidates `gemini-3.7-flash-high` and `gemini-3.7-flash-advisor` are ambiguous and must be refused unless one exact common ID is explicitly selected.
- `cliproxy-models` owns a guarded seven-file Codex configuration transaction: base `config.toml` plus `cliproxy-grok-4-6.config.toml` `cliproxy-gemini-3-7-flash.config.toml`, `cliproxy-luna.config.toml`, `luna-grok.config.toml`, and `grok-gemini.config.toml` overlays, plus the owned derived `cliproxy-council-models.json` snapshot.
- Never write managed `[profiles.*]` tables or a managed top-level `profile` selector. Codex 0.134.0+ uses separate profile overlay files.
- Preserve unrelated TOML/comments only where ownership is unambiguous; unmanaged collisions, malformed TOML/markers, symlinks, non-regular files, or concurrent changes fail closed.
- Base/profile writes must be one backup-aware, permission-restricted, atomic, post-validated, idempotent transaction with exact rollback.
- Support both release-bound source and versioned plugin-cache authority layouts without hardcoded home paths. Never choose an arbitrary cached authority version.
- `codex-moa` remains native to Codex subagents and its checkpoint-only MCP server. Do not add Hermes, another scheduler, model loop, gateway, or orchestration runtime.
- The MCP server receives only `CODEX_HOME`; it cannot call models, execute code, or receive proxy authority.
- Supported councils are `luna-grok` (exact Luna root, Grok reviewer) and `grok-gemini` (Grok root, Gemini High reviewer). Gemini-led new runs are unsupported. Named profile root instructions must not impose leader obligations on child advisors.
- New checkpoint writes use schema 2 and bind council/model identity with native final-review witnesses; historical schema 1 remains read-only. A valid witness shape is not authenticated evidence: audit native runtime events.
- Keep single-writer ownership, bounded fanout/recovery, repository-native validation, and independent final review.
- `.bootstrap/`, `native-moa.b64.part-*`, `materialize-native-moa.yml`, and `plugins/hermes-moa` remain physically absent.

## Change workflow

1. Verify exact main/branch guards.
2. Inspect release/manifest/authority contracts and affected production paths/tests.
3. Make one coherent authority-preserving change.
4. Align versions, docs, tests, and changelog.
5. Run every gate in README.md.
6. Independently reread the exact PR diff and checks.
7. Merge only when green; never publish or move a release tag during implementation.

Do not claim a live VPS2/Codex gate unless it ran against the exact commit being adjudicated. Preserve the prior evidence in `docs/VPS2_GATE_2026-08-30.md` without treating it as a waiver for the post-correction gate.
