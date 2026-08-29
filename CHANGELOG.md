# Changelog

All notable user-visible changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow semantic versioning.

## [Unreleased]

### Changed

- Nothing yet.

## [1.0.0] - 2026-08-29

### Added

- Standalone Codex marketplace and `cliproxy-models` plugin.
- Exact Grok 4.6 and Gemini 3.7 Flash profile admission through one CLIProxyAPI provider.
- Validation of both OpenAI-compatible and Codex-compatible CLIProxyAPI model catalogs.
- Fail-closed endpoint, alias, provider-collision, and current-model checks.
- Secret-safe `CLIPROXY_URL` and `CLIPROXY_API_KEY` launch contract.
- Atomic, mode-`0600`, timestamp-backed-up, byte-idempotent Codex configuration writes.
- Codex skill, setup/status/use commands, direct Python entry point, and deterministic regression tests.
- Agent, setup, contribution, security, and release documentation.
- Tag-driven validation, packaging, checksum, and GitHub release workflow.

[Unreleased]: https://github.com/vai8havchoudhary/codex/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/vai8havchoudhary/codex/releases/tag/v1.0.0
