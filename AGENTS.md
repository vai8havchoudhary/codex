# Repository instructions

This repository is the `cliproxy` Codex plugin marketplace, not an OpenAI Codex source fork.

Read [agent.md](agent.md) before non-trivial changes. It is the architecture and operations handbook; this file contains mandatory rules Codex should load automatically.

## Marketplace invariants

- Marketplace name remains `cliproxy`.
- Every `plugins/<name>` directory, manifest `name`, skill `name`, marketplace entry, and release mapping must agree.
- Current plugins are `cliproxy-models` and `hermes-moa`.
- `release.json` is the marketplace release/version authority; its plugin-version map must equal every plugin manifest.

## Authority and security invariants

- Maintain exactly one CLIProxyAPI provider in each target application. Never create providers per upstream Grok or Gemini account.
- Never read, enumerate, print, log, summarize, or persist CLIProxyAPI account data or the value of `CLIPROXY_API_KEY`.
- Store only the environment-variable name `CLIPROXY_API_KEY` in Codex or Hermes configuration.
- Require exact Grok 4.6 and Gemini 3.7 Flash IDs in both CLIProxyAPI catalogs.
- Reject ambiguity, nearby versions, malformed endpoints, unrelated provider collisions, foreign Hermes preset collisions, and unsafe non-loopback HTTP.
- Keep mutations fail closed, timestamp-backed-up, post-validated, and byte-idempotent; restore exact original bytes after partial failure.
- Preserve unrelated `~/.codex/config.toml` and `~/.hermes/config.yaml` content.
- Do not change CLIProxyAPI routing, credentials, quotas, aliases, or account files.

## Hermes-specific invariants

- Use Hermes' built-in virtual provider `moa`; do not implement a parallel orchestration runtime.
- Use one named custom provider `cliproxy` with `transport: openai_chat` and `key_env: CLIPROXY_API_KEY`.
- `cliproxy-grok-led` means Gemini reference advisor and Grok acting aggregator.
- `cliproxy-gemini-led` means Grok reference advisor and Gemini acting aggregator.
- The aggregator is the acting model; reference models advise before it.
- Preserve `privacy_filter: full` when already selected.

## Change workflow

1. Inspect marketplace, release metadata, affected manifests/skills/scripts, root docs, workflows, and tests.
2. Make one coherent vertical change without duplicate configuration paths.
3. Update setup/security/release documentation when behavior changes.
4. Align `release.json`, plugin manifests, and `CHANGELOG.md` for released changes.
5. Run every command under **Development validation** in `README.md`.
6. Follow `docs/RELEASING.md` for tags or guarded promotion branches.

Do not claim a live CLIProxyAPI, Codex Desktop, or Hermes Agent smoke test unless it actually ran.
