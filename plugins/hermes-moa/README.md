# Hermes MoA via CLIProxyAPI

This Codex plugin configures Hermes Agent's built-in Mixture-of-Agents provider to use the exact Grok 4.6 and Gemini 3.7 Flash aliases already exported by CLIProxyAPI.

It creates two presets:

| Preset | Reference advisor | Acting aggregator |
|---|---|---|
| `cliproxy-grok-led` | Gemini 3.7 Flash | Grok 4.6 |
| `cliproxy-gemini-led` | Grok 4.6 | Gemini 3.7 Flash |

Both roles use one Hermes provider named `cliproxy`. CLIProxyAPI remains authoritative for every upstream account, credential, quota, retry, health check, and failover decision.

## Required environment

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Hermes Agent must be installed and expose the `hermes moa` and `hermes config` commands.

## Use through Codex

```text
@hermes-moa Set up Hermes MoA with Grok leading.
@hermes-moa Check my Hermes MoA configuration.
@hermes-moa Switch Hermes MoA to Gemini leading.
```

## Direct entry point

```bash
python3 scripts/plugin.py status
python3 scripts/plugin.py setup grok-led
python3 scripts/plugin.py setup gemini-led
python3 scripts/plugin.py use grok-led
python3 scripts/plugin.py use gemini-led
```

After setup, Hermes supports either a persistent selection:

```text
/model cliproxy-grok-led --provider moa
```

or a one-shot MoA request using the configured default preset:

```text
/moa Review this implementation and propose the safest patch.
```

The plugin validates both CLIProxyAPI model catalogs, rejects ambiguous or nearby model versions, writes only the environment-variable name `CLIPROXY_API_KEY`, preserves unrelated Hermes configuration, backs up changed files, and rolls back exact original bytes when any write or post-validation fails.

Implementation compatibility was designed against Hermes Agent source commit `299c652a66bcc915a2a1e10cd2b648f196ec4bba` and its documented MoA/provider configuration contracts.
