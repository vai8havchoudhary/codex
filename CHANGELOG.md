# Changelog

All notable user-visible changes are documented here. Versions follow semantic versioning.

## [Unreleased]

### Changed

- Nothing yet.

## [2.0.0] - 2026-08-30

### Added

- Native `codex-moa` plugin using Codex subagents, model overrides, agent definitions, skills, commands, and a narrow checkpoint MCP server.
- Grok-led and Gemini-led long-horizon coding policies with single-writer ownership, bounded model-diverse councils, validation-led recovery, independent final review, and opaque resume checkpoints.
- Immutable checkpoint schema, secret-field refusal, atomic mode-`0600` records, mode-`0700` storage, digest verification, and idempotent equal writes.
- Research mapping for localization, planning, modular specialization, model diversity, feedback-driven repair, and durable memory.
- VPS2 regression coverage for `grok-4.6` plus ambiguous `gemini-3.7-flash-high` / `gemini-3.7-flash-advisor` catalogs.
- Exact explicit Gemini alias admission when the selected ID appears in both CLIProxyAPI catalogs.
- Packaged `codex-moa/authority.json` compatibility contract binding marketplace bundle `2.0.0`, `codex-moa` `2.0.0`, and `cliproxy-models` `1.0.0`.

### Changed

- Marketplace bundle authority advanced to `2.0.0` with exactly `cliproxy-models` and `codex-moa`.
- Validation and release workflows now validate every plugin manifest, test suite, and MCP configuration.
- Documentation now treats both components as native Codex plugins and removes Hermes setup/runtime instructions.
- Native preflight now locates `cliproxy-models` in both release-bound source checkouts and Codex's real versioned plugin cache, selecting only the exact pinned authority version and refusing missing, incompatible, or ambiguous alternatives.

### Removed

- `hermes-moa` and every Hermes Agent runtime/configuration dependency.
- Broken `.bootstrap/native-moa.b64.part-*` payload delivery.
- One-shot `materialize-native-moa.yml` reconstruction workflow.

## [1.1.0] - 2026-08-29

### Added

- Historical Hermes MoA integration. Superseded and removed by `2.0.0`.

## [1.0.0] - 2026-08-29

### Added

- Standalone Codex marketplace and `cliproxy-models` plugin.
- Exact Grok 4.6 and Gemini 3.7 Flash profile admission through one CLIProxyAPI provider.
- Atomic, backed-up, byte-idempotent Codex configuration writes and release automation.

[Unreleased]: https://github.com/vai8havchoudhary/codex/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/vai8havchoudhary/codex/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/vai8havchoudhary/codex/releases/tag/v1.1.0
[1.0.0]: https://github.com/vai8havchoudhary/codex/releases/tag/v1.0.0
