# Changelog

All notable user-visible changes are documented here. Versions follow semantic versioning.

## [Unreleased]

### Changed

- Added canonical `luna-grok` and `grok-gemini` profiles, skills, and commands in the existing two-plugin bundle; no additional runtime.
- Admitted exact `gpt-5.6-luna` through both catalogs, with standalone setup/use and a guarded seven-file transaction: six TOMLs and a live-derived model-catalog snapshot. Named profiles pin native model metadata without changing the base default's catalog.
- Refused unsupported Gemini-led new runs and added schema-2 native final-review witnesses with identity-bound chains; schema-1 history remains readable.
- Reduced redundant Luna council work: reuse one localizer/critic and reserve a proven read-only final reviewer before editing.
- Split Gemini into fresh single-turn evidence-only native plan criticism and final review, with complete packets, bounded transport retries and explicit evidence limitations; no claim to fix Gemini continuation. Luna generated instructions are unchanged.
- Enforced fresh Gemini final-reviewer IDs for new writes across same-run history while preserving historical schema-1/schema-2 digests; exposed precise MCP evidence/validation/native witness item schemas without changing stored shapes.
- Retained untagged 2.0.0 candidate and 1.1.0 authority versions: correctness correction, not cachebuster churn. No tag/release or stale promotion branch changed.
- Aligned final-review instructions with `APPROVE` / `REQUEST_CHANGES`, preserving negative review evidence without allowing completion.
- Fail closed before mutation when the two-council installation is asked to use a noncanonical Gemini alias; refreshed public security/privacy disclosures for all seven local artifacts and unauthenticated native witness claims.

## [2.0.0] - 2026-08-30

### Added

- Native `codex-moa` 2.0.0 plugin using Codex subagents, model overrides, agent definitions, skills, commands, and a narrow checkpoint MCP server.
- Initial Grok-led and Gemini-led long-horizon policies (Gemini-led later found unsupported; corrected before publication) with single-writer ownership, bounded councils, validation-led recovery, independent final review, and opaque resume checkpoints.
- VPS2 regression coverage for `grok-4.6` plus ambiguous `gemini-3.7-flash-high` / `gemini-3.7-flash-advisor` catalogs.
- Packaged `codex-moa/authority.json` contract binding the bundle and exact installed model authority.
- `cliproxy-models` 1.1.0 modern Codex profile-file support.

### Changed

- Marketplace bundle authority is `2.0.0` with exactly `cliproxy-models` 1.1.0 and `codex-moa` 2.0.0.
- Model setup now writes one base `config.toml` plus `cliproxy-grok-4-6.config.toml` and `cliproxy-gemini-3-7-flash.config.toml` overlays; it no longer emits managed `[profiles.*]` tables or a managed top-level selector.
- The model setup migration is a coordinated three-file transaction with mode-`0600` writes, backups, concurrency checks, post-validation, idempotence, collision/symlink refusal, and exact rollback.
- Native preflight now validates the base provider and both separate profile overlays and locates only `cliproxy-models` 1.1.0 in release-bound source or versioned-cache layouts.
- Documentation records the exact pre-correction VPS2 provider/MCP/council PASS and the profile blocker without treating the earlier PASS as final release approval.

### Removed

- `hermes-moa` and every Hermes runtime/config dependency.
- Broken bootstrap payload delivery and one-shot source materialization workflow.
- Managed legacy Codex profile tables from the model installer.

## [1.1.0] - 2026-08-29

### Added

- Historical Hermes MoA integration. Superseded and removed by marketplace bundle 2.0.0.

## [1.0.0] - 2026-08-29

### Added

- Standalone Codex marketplace and `cliproxy-models` 1.0.0.
- Exact Grok 4.6 and Gemini 3.7 Flash admission through one CLIProxyAPI provider.
- Historical single-file configuration writer. Superseded by `cliproxy-models` 1.1.0 in bundle 2.0.0.

[Unreleased]: https://github.com/vai8havchoudhary/codex/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/vai8havchoudhary/codex/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/vai8havchoudhary/codex/releases/tag/v1.1.0
[1.0.0]: https://github.com/vai8havchoudhary/codex/releases/tag/v1.0.0
