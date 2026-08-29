# Changelog

All notable user-visible changes are documented here. Versions follow semantic versioning for the marketplace bundle defined by `release.json`.

## [Unreleased]

### Changed

- Nothing yet.

## [1.1.0] - 2026-08-29

### Added

- `hermes-moa` Codex plugin for configuring Hermes Agent's built-in Mixture-of-Agents provider.
- One `cliproxy` Hermes provider backed by `CLIPROXY_URL` and the environment-variable name `CLIPROXY_API_KEY`.
- Grok-led and Gemini-led cross-model presets with exact dual-catalog alias admission.
- Transactional Hermes config mutation, foreign-collision refusal, exact rollback, backups, idempotence, named-profile support, status, tuning, and switching.
- Marketplace-bundle release metadata and multi-plugin validation/packaging.

## [1.0.0] - 2026-08-29

### Added

- Standalone Codex marketplace and `cliproxy-models` plugin.
- Exact Grok 4.6 and Gemini 3.7 Flash profile admission through one CLIProxyAPI provider.
- Secret-safe endpoint/key environment contract, atomic Codex config writes, tests, docs, checksums, and GitHub release automation.

[Unreleased]: https://github.com/vai8havchoudhary/codex/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/vai8havchoudhary/codex/releases/tag/v1.1.0
[1.0.0]: https://github.com/vai8havchoudhary/codex/releases/tag/v1.0.0
