---
name: hermes-moa
description: Configure, verify, tune, or switch Hermes Agent Mixture-of-Agents presets that use CLIProxyAPI-backed Grok 4.6 and Gemini 3.7 Flash. Use when a user mentions Hermes Agent, Mixture of Agents, MoA, /moa, Grok-led or Gemini-led orchestration, or using multiple CLIProxyAPI models together.
---

# Hermes MoA via CLIProxyAPI

Use the bundled `../../scripts/plugin.py` for every check and mutation. Resolve it relative to this `SKILL.md`; do not recreate configuration logic in the user's project and do not edit `~/.hermes/config.yaml` directly.

## Non-negotiable security rules

1. Never print, quote, summarize, log, or persist the value of `CLIPROXY_API_KEY`.
2. Never read or enumerate CLIProxyAPI upstream account files.
3. Configure exactly one Hermes provider, `cliproxy`; never create a provider per upstream account.
4. Store only `key_env: CLIPROXY_API_KEY` in Hermes configuration.
5. Plain HTTP is allowed only for `localhost`, `127.0.0.1`, or `::1`; remote endpoints require HTTPS.
6. Admit only exact Grok 4.6 and Gemini 3.7 Flash IDs present in both CLIProxyAPI catalogs.
7. Fail closed on missing Hermes MoA support, foreign provider/preset collisions, malformed config, partial writes, or post-validation mismatch.

## Expected environment

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Check only whether these variables are set. Never echo their values.

## Status or diagnosis

Run:

```bash
python3 <absolute-plugin-script> status
```

A successful status proves exact provider and model-route custody. Exit status 2 means setup is absent or mismatched; report the typed missing/mismatched paths without editing anything.

## Setup or repair

Choose `grok-led` unless the user explicitly asks for Gemini to act. Run exactly one:

```bash
python3 <absolute-plugin-script> setup grok-led
python3 <absolute-plugin-script> setup gemini-led
```

The setup creates both presets:

- `cliproxy-grok-led`: Gemini reference advisor, Grok acting aggregator.
- `cliproxy-gemini-led`: Grok reference advisor, Gemini acting aggregator.

Defaults are `reference_max_tokens: 600`, `max_tokens: 4096`, `fanout: user_turn`, and `privacy_filter: display`. Preserve an existing stronger `privacy_filter: full` setting. Use `--force` only when the user explicitly authorizes replacing a foreign provider or preset collision.

Report the endpoint origin, admitted aliases, active preset, config path, backup path when emitted, and whether bytes changed. Never report a secret value. Tell the user to restart Hermes or begin a new Hermes session.

## Switch the acting model

After status succeeds, run exactly one:

```bash
python3 <absolute-plugin-script> use grok-led
python3 <absolute-plugin-script> use gemini-led
```

This changes only `moa.default_preset` and the main Hermes `model` selection while preserving both presets and unrelated Hermes settings.

## Using MoA inside Hermes

For a persistent model selection in Hermes:

```text
/model cliproxy-grok-led --provider moa
/model cliproxy-gemini-led --provider moa
```

For a one-shot request with the configured default preset:

```text
/moa <prompt>
```

The reference model advises first; the aggregator is the acting model that writes the user-visible answer and performs tool calls. `user_turn` fan-out runs references once per user turn, which is the default cost-conscious cadence.

## Interpretation rules

- `already up to date` is successful byte-idempotence.
- A timestamped backup is created only when an existing Hermes config changes.
- Setup writes whole provider/preset objects through Hermes' own `config set` surface, preserving unrelated object fields.
- A failed write restores the exact original `config.yaml` bytes or removes a newly created partial file.
- The plugin configures Hermes only; it never changes CLIProxyAPI accounts, credentials, aliases, or routing policy.
