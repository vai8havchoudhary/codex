# Repository instructions

This repository is the `cliproxy` Codex plugin marketplace, not an OpenAI Codex source fork.

Read [agent.md](agent.md) before making non-trivial changes. It is the architecture and operations handbook; this file contains the mandatory rules Codex should load automatically.

## Non-negotiable invariants

- Keep the marketplace entry, plugin directory, manifest name, and skill name aligned to `cliproxy-models`.
- Maintain exactly one Codex provider for CLIProxyAPI. Never create providers per upstream Grok or Gemini account.
- Never read, enumerate, print, log, summarize, or persist CLIProxyAPI account data or the value of `CLIPROXY_API_KEY`.
- Store only the environment-variable name `CLIPROXY_API_KEY` in Codex configuration.
- Require exact Grok 4.6 and Gemini 3.7 Flash aliases in both the OpenAI-compatible and Codex-compatible provider catalogs.
- Reject ambiguity, nearby versions, malformed endpoints, unrelated provider collisions, and unsafe non-loopback HTTP.
- Keep configuration changes fail closed, atomic, mode `0600`, timestamp-backed-up, post-validated, and byte-idempotent.
- Preserve unrelated `~/.codex/config.toml` content and comments.
- Do not change CLIProxyAPI routing, credentials, quotas, or account files.

## Change workflow

1. Inspect the marketplace manifest, plugin manifest, skill, entry point, installer, and relevant tests.
2. Make the smallest coherent change; avoid duplicate setup paths or account-specific configuration.
3. Update user-facing setup or release documentation when behavior, prerequisites, or commands change.
4. Keep the plugin version and `CHANGELOG.md` aligned for release changes.
5. Run every command under **Development validation** in `README.md`.
6. For release work, also follow `docs/RELEASING.md` and verify the tag will equal `v<plugin version>`.

Do not claim a live CLIProxyAPI or Codex Desktop smoke test unless it was actually run.
