---
name: cliproxy-models
description: Configure, verify, or switch CLIProxyAPI-backed Grok 4.6 and Gemini 3.7 Flash models in Codex Desktop. Use when a user mentions CLIProxyAPI, CLIPROXY_URL, CLIPROXY_API_KEY, Grok 4.6, Gemini 3.7 Flash, custom Codex model providers, or adding these models to the Codex app.
---

# CLIProxyAPI Models

Use the bundled `../../scripts/plugin.py` entry point for every check and mutation. Resolve it relative to this `SKILL.md`; do not recreate the installer in the user's project.

## Security rules

1. Never print, quote, summarize, log, or persist the value of `CLIPROXY_API_KEY`.
2. Never read or enumerate CLIProxyAPI upstream account files. Multiple-account routing belongs exclusively to CLIProxyAPI.
3. Never create one Codex provider per upstream account.
4. Store only `env_key = "CLIPROXY_API_KEY"` in Codex configuration.
5. Fail closed when the endpoint, catalogs, aliases, current configuration, or mutation is ambiguous.
6. Plain HTTP is loopback-only; remote endpoints require HTTPS.

## Expected environment

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Check only whether the variables are set. Never echo their values.

## Setup or repair

1. Run `python3 <absolute-plugin-script> status`.
2. If status fails, report the typed failure and do not edit Codex configuration.
3. Select `grok` for an explicit Grok request or no preference; select `gemini` for an explicit Gemini request.
4. Run `python3 <absolute-plugin-script> setup <choice>` exactly once.
5. Report the provider ID, admitted aliases, config path, backup path when emitted, and whether bytes changed.
6. Tell the user to fully quit and reopen Codex Desktop.

## Status or diagnosis

Run:

```bash
python3 <absolute-plugin-script> status
```

This performs a dry-run catalog and configuration admission. Report only endpoint origin, selected aliases, provider ID, and typed errors. Never claim success when the command fails.

## Switch model

Run exactly one of:

```bash
python3 <absolute-plugin-script> use grok
python3 <absolute-plugin-script> use gemini
```

Tell the user to start a new thread or reopen Codex Desktop after success.

## Interpretation rules

- `already up to date` is successful idempotence.
- A backup is created only when configuration bytes change.
- Both aliases must appear in the OpenAI-compatible and Codex-compatible CLIProxyAPI catalogs.
- Multiple matching aliases require explicit `--grok-model` or `--gemini-model` selection through the bundled entry point.
- The plugin changes Codex configuration only; it never changes CLIProxyAPI accounts or credentials.
