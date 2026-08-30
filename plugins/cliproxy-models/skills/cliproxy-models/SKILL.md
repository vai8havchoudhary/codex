---
name: cliproxy-models
description: Configure, verify, migrate, or switch CLIProxyAPI-backed Grok 4.6 and Gemini 3.7 Flash models in Codex. Use for CLIProxyAPI, CLIPROXY_URL, CLIPROXY_API_KEY, custom providers, modern Codex profile files, or adding these models to the Codex app.
---

# CLIProxyAPI Models

Use the bundled `../../scripts/plugin.py` for every check and mutation. Resolve it relative to this skill; do not recreate the installer in a project repository.

## Security and authority rules

1. Never print, log, summarize, or persist the value of `CLIPROXY_API_KEY`.
2. Never read or enumerate CLIProxyAPI account files. Account routing belongs only to CLIProxyAPI.
3. Keep exactly one Codex provider for all proxy-managed accounts.
4. Store only `env_key = "CLIPROXY_API_KEY"`.
5. Require the exact model ID in both CLIProxyAPI catalogs.
6. Refuse ambiguous aliases, unsafe endpoints, malformed TOML, symlinks, unmanaged collisions, or partial configuration.
7. Plain HTTP is loopback-only; remote endpoints require HTTPS.

## Modern profile-file contract

Codex loads the base file and then overlays the selected profile file:

```text
~/.codex/config.toml
~/.codex/cliproxy-grok-4-6.config.toml
~/.codex/cliproxy-gemini-3-7-flash.config.toml
```

The base file owns the shared provider and selected default. Each overlay owns only managed top-level `model` and `model_provider` keys while preserving unrelated settings. Never add a top-level `profile` selector or `[profiles.*]` table.

The setup transaction must write or migrate all three documents together with backups, mode `0600`, post-validation, idempotence, and exact rollback on failure.

## Expected environment

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Check only whether the variables are set. Never echo their values.

## Setup or repair

1. Run `python3 <absolute-plugin-script> status`.
2. If status reports alias ambiguity, request an explicit exact `--gemini-model` or `--grok-model`; do not guess.
3. Run `python3 <absolute-plugin-script> [exact alias flags] setup grok|gemini` once.
4. Report provider ID, admitted aliases, all changed paths, backup paths, and whether the transaction was already up to date.
5. Tell the user to fully quit and reopen Codex.

For the current VPS2 catalog, a valid explicit example is:

```bash
python3 <absolute-plugin-script> \
  --gemini-model gemini-3.7-flash-high \
  setup grok
```

## Status and switching

```bash
python3 <absolute-plugin-script> status
python3 <absolute-plugin-script> use grok
python3 <absolute-plugin-script> use gemini
```

`status` is a dry-run admission and document validation. `use` changes the base default while retaining both modern overlays. `already up to date` is successful idempotence.
