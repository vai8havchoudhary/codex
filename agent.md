# Architecture and maintainer handbook

## Product boundary

### `cliproxy-models` 1.1.0

The sole model-admission and Codex-provider configuration authority. It reads both CLIProxyAPI catalogs, admits exact common IDs, refuses ambiguity, and writes one provider plus two modern profile overlays. It never inspects proxy accounts or chooses routing policy.

Managed documents:

```text
~/.codex/config.toml
~/.codex/cliproxy-grok-4-6.config.toml
~/.codex/cliproxy-gemini-3-7-flash.config.toml
```

The base owns the shared provider and selected default. Each overlay owns managed top-level `model` and `model_provider` keys. Legacy `[profiles.*]` tables and top-level profile selectors are not current Codex configuration.

The three paths form one transaction: snapshot, ownership/path validation, coordinated backups, atomic replacements, post-validation, and exact rollback. Existing files become mode `0600`; new files are created mode `0600`. Equal bytes and safe modes are a no-op. User-owned collisions and malformed or unsafe paths are refused rather than overwritten.

### `codex-moa` 2.0.0

A native Codex coordination policy using Codex's own agent tree, model overrides, messaging, bounded forks, skills, commands, and checkpoint MCP server. It contains no external model loop.

The root is the coordinator and default single writer. The opposite model is consulted at localization, plan criticism, concrete-failure recovery, and independent final review—not after every step.

## Packaged authority dependency

```text
marketplace:       cliproxy
release:           cliproxy-plugins 2.0.0
consumer:          codex-moa 2.0.0
model authority:   cliproxy-models 1.1.0
required scripts:  catalog.py, plugin.py
```

Source and installed-cache discovery are release/pin bound. No highest/newest/first-version selection is allowed. Preflight loads model admission from the exact authority, then validates the provider in base `config.toml` and both sibling overlay files.

## Live alias contract

VPS2 evidence on 2026-08-30 shows `grok-4.6`, `gemini-3.7-flash-high`, and `gemini-3.7-flash-advisor`, with no bare Gemini alias. Automatic Gemini resolution must fail. Explicit `--gemini-model gemini-3.7-flash-high` is accepted only when present in both catalogs and equal to the profile overlay.

## Native council lifecycle

```text
preflight -> localize -> plan -> implement -> validate -> review -> complete
                                      |           |
                                      +-> recover-+
```

- localize before editing;
- accept one dependency-aware plan;
- keep one writer unless disjoint ownership is explicit;
- treat repository gates as authoritative;
- allow at most two coherent repair rounds per blocker;
- record immutable checkpoints and reconcile live state on resume;
- require an opposite-model final review of the actual diff and evidence.

## Checkpoint MCP boundary

The MCP is a state store, not an orchestrator. It receives only `CODEX_HOME`, stores compact immutable mode-`0600` records beneath a mode-`0700` directory, rejects secret fields/values and symlinks, and cannot call models or execute repository commands.

## Release authority

`release.json`, plugin manifests, and `authority.json` must align before validation succeeds. Bundle 2.0.0 intentionally includes a new `cliproxy-models` 1.1.0 because the historically released 1.0.0 bytes used obsolete profile tables and are immutable.

The pre-correction exact-main provider/MCP/council evidence is documented in `docs/VPS2_GATE_2026-08-30.md`. A fresh exact-main reinstall and profile/council gate is still mandatory before creating `v2.0.0`.

Fail closed when exact aliases, authority versions, profile documents, repository authority, writer ownership, checkpoint safety, or validation evidence are unresolved.
