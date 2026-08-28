# CLIProxyAPI Models for Codex

A standalone Codex plugin marketplace that adds exact **Grok 4.6** and **Gemini 3.7 Flash** profiles through one CLIProxyAPI model provider.

CLIProxyAPI remains authoritative for all upstream accounts, OAuth sessions, quota balancing, health checks, retries, and failover. Codex receives one endpoint and stable aliases; this plugin never copies account identifiers or API-key values into `~/.codex/config.toml`.

## Install

Export the local proxy contract exactly once in the environment that launches Codex:

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Add this repository as a marketplace and install its plugin:

```bash
codex plugin marketplace add vai8havchoudhary/codex
codex plugin add cliproxy-models@cliproxy
```

Start a new Codex session after installation. A Codex Desktop process launched from Finder may not inherit terminal exports; launch it from the configured terminal or set the same variables in its launch environment.

## Configure the models

Ask the installed plugin:

```text
@cliproxy-models Set up CLIProxyAPI models and use Grok 4.6 by default.
```

The plugin validates both model-catalog contracts before changing configuration:

```text
GET /v1/models
GET /v1/models?client_version=...
```

The repository checkout also exposes a direct entry point:

```bash
python3 plugins/cliproxy-models/scripts/plugin.py status
python3 plugins/cliproxy-models/scripts/plugin.py setup grok
python3 plugins/cliproxy-models/scripts/plugin.py use gemini
```

Fully quit and reopen Codex Desktop after setup or switching.

## Profiles

```text
cliproxy-grok-4-6
cliproxy-gemini-3-7-flash
```

Both profiles reference one provider, `cliproxyapi`. Multiple upstream Grok and Gemini accounts remain entirely behind CLIProxyAPI.

## Safety properties

- Exact-version admission only. Nearby variants such as `grok-4.60`, `grok-4.6.1`, marker-less `gemini-3.7`, and ambiguous aliases are refused.
- An admitted alias must appear in both the OpenAI-compatible and Codex-compatible CLIProxyAPI catalogs.
- Plain HTTP is accepted only for localhost and loopback endpoints. Remote endpoints require HTTPS.
- `CLIPROXY_API_KEY` values are never printed or persisted; Codex stores only `env_key = "CLIPROXY_API_KEY"`.
- Existing unrelated provider definitions are never repurposed.
- Configuration writes are atomic, mode `0600`, timestamp-backed-up, post-validated, and byte-idempotent.
- Plugin installation does not enumerate or alter CLIProxyAPI account files.

## Validate

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s plugins/cliproxy-models/scripts -p 'test_*.py' -v
python3 -m py_compile plugins/cliproxy-models/scripts/*.py
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 -m json.tool plugins/cliproxy-models/.codex-plugin/plugin.json >/dev/null
```

## Repository replacement

The previous Codex source-fork tree remains recoverable through Git history and the `archive/codex-upstream-20260828` branch. The current `main` branch is exclusively this plugin marketplace.
