# Repository instructions

This repository is the `cliproxy` Codex plugin marketplace. It contains exactly two native Codex plugins:

- `cliproxy-models`
- `codex-moa`

Read [agent.md](agent.md) before non-trivial changes.

## Non-negotiable invariants

- Keep marketplace, directory, manifest, skill, and release names aligned.
- `release.json` is the marketplace bundle version authority.
- Maintain exactly one Codex provider for CLIProxyAPI. Never create providers per upstream account.
- Never read, enumerate, print, summarize, or persist proxy account files or the value of `CLIPROXY_API_KEY`.
- Store only the environment-variable name `CLIPROXY_API_KEY` in Codex configuration.
- Require exact Grok 4.6 and Gemini 3.7 Flash aliases in both CLIProxyAPI catalogs.
- Current VPS2 evidence includes `grok-4.6`, `gemini-3.7-flash-high`, and `gemini-3.7-flash-advisor`, with no bare Gemini alias. Automatic selection must refuse the ambiguity; an explicit exact common alias may be admitted.
- Keep `codex-moa` native to Codex subagents, model overrides, skills, commands, agent definitions, and its checkpoint MCP server.
- Do not add Hermes Agent, another scheduler, a second model gateway, or a parallel orchestration runtime.
- The checkpoint MCP server may store compact immutable state only. It must not execute code, call models, receive the proxy key, or route accounts.
- Preserve single-writer ownership, bounded fanout, bounded recovery, repository-native validation, and independent final review.
- Keep configuration and checkpoint writes fail closed, atomic, permission-restricted, post-validated, and idempotent.
- `.bootstrap/`, `native-moa.b64.part-*`, and `materialize-native-moa.yml` must remain physically absent.

## Change workflow

1. Inspect marketplace/release authority, both plugin manifests, relevant skills/commands/agents, MCP config/server, and tests.
2. Make one coherent change without duplicating model admission or orchestration authority.
3. Update tests and user docs for changed behavior or live alias evidence.
4. Align manifest versions, `release.json`, and `CHANGELOG.md` for release changes.
5. Run every command under **Development validation** in `README.md`.
6. Reread the exact diff and GitHub checks before merge.
7. For publication, follow `docs/RELEASING.md`. Never create or move a release tag during ordinary implementation.

Do not claim a live CLIProxyAPI, Codex Desktop, or VPS2 gate unless it was actually run on the exact commit being adjudicated.
