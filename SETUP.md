# Setup and operations

This guide installs, verifies, upgrades, switches, rolls back, and removes the `cliproxy-models` Codex plugin.

## 1. Prerequisites

You need:

- Codex with the `codex plugin` marketplace commands;
- Python 3.11 or newer;
- CLIProxyAPI listening locally or at an HTTPS endpoint;
- a CLIProxyAPI access key;
- exact Grok 4.6 and Gemini 3.7 Flash aliases exported by CLIProxyAPI.

The plugin does not configure CLIProxyAPI accounts. Add and authenticate all upstream accounts in CLIProxyAPI first.

## 2. Configure the launch environment

For the standard local CLIProxyAPI installation:

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Do not echo `CLIPROXY_API_KEY`, add it to shell tracing, commit it, or paste it into Codex configuration.

Confirm only that both variables are present:

```bash
test -n "${CLIPROXY_URL:-}" && echo "CLIPROXY_URL is set"
test -n "${CLIPROXY_API_KEY:-}" && echo "CLIPROXY_API_KEY is set"
```

A Codex Desktop process launched outside this environment may not inherit the variables. Launch Codex from the configured environment or configure the same variables in the application launch environment. Fully quit the app before changing its launch environment.

### Remote proxy endpoint

Use HTTPS for non-loopback endpoints:

```bash
export CLIPROXY_URL=https://proxy.example.com
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Plain HTTP is deliberately rejected unless the hostname is `localhost`, `127.0.0.1`, or `::1`.

## 3. Install the marketplace and plugin

Add the marketplace from this repository:

```bash
codex plugin marketplace add vai8havchoudhary/codex --ref main
```

Install the plugin:

```bash
codex plugin add cliproxy-models@cliproxy
```

Verify discovery:

```bash
codex plugin marketplace list --json
codex plugin list --marketplace cliproxy --json
```

The marketplace name is `cliproxy`; the plugin name is `cliproxy-models`.

## 4. Configure the model profiles

Start a new Codex session and invoke the plugin.

Use Grok by default:

```text
@cliproxy-models Set up CLIProxyAPI models and use Grok 4.6 by default.
```

Use Gemini by default:

```text
@cliproxy-models Set up CLIProxyAPI models and use Gemini 3.7 Flash by default.
```

The setup preflight checks:

1. endpoint shape and transport safety;
2. `CLIPROXY_API_KEY` presence;
3. `GET /v1/models`;
4. `GET /v1/models?client_version=...`;
5. exact alias presence in both catalogs;
6. existing Codex provider/profile collisions;
7. generated TOML validity before writing.

On success, the plugin creates or repairs:

```text
provider: cliproxyapi
profile:  cliproxy-grok-4-6
profile:  cliproxy-gemini-3-7-flash
```

The secret value is not written. Codex stores only:

```toml
env_key = "CLIPROXY_API_KEY"
```

Fully quit and reopen Codex Desktop after setup.

## 5. Verify status

From Codex:

```text
@cliproxy-models Check my CLIProxyAPI model setup.
```

From a repository checkout:

```bash
python3 plugins/cliproxy-models/scripts/plugin.py status
```

A successful status check reports the provider ID and admitted model aliases without changing the active model or printing the API key.

## 6. Switch the default model

From Codex:

```text
@cliproxy-models Switch Codex to Grok 4.6.
```

or:

```text
@cliproxy-models Switch Codex to Gemini 3.7 Flash.
```

From a repository checkout:

```bash
python3 plugins/cliproxy-models/scripts/plugin.py use grok
python3 plugins/cliproxy-models/scripts/plugin.py use gemini
```

Start a new thread or reopen Codex Desktop after a successful switch.

## 7. Multiple matching aliases

CLIProxyAPI should ideally expose one stable alias for each supported model. When it intentionally exposes multiple matching aliases, select exact IDs from a repository checkout:

```bash
python3 plugins/cliproxy-models/scripts/plugin.py \
  --grok-model 'EXACT_GROK_4_6_ALIAS' \
  --gemini-model 'EXACT_GEMINI_3_7_FLASH_ALIAS' \
  setup grok
```

Explicit aliases are still required to:

- exist in both model catalogs;
- match the requested family and exact version;
- include `flash` for Gemini 3.7.

The plugin never chooses an account-specific alias by guessing.

## 8. Upgrade

Refresh the marketplace snapshot:

```bash
codex plugin marketplace upgrade cliproxy
```

Reinstall or refresh the plugin through the Codex plugin UI/CLI, then run:

```text
@cliproxy-models Check my CLIProxyAPI model setup.
```

Read [CHANGELOG.md](CHANGELOG.md) before upgrading across minor or major versions.

## 9. Roll back a configuration change

When a write changes `~/.codex/config.toml`, the installer reports a timestamped backup such as:

```text
~/.codex/config.toml.bak.20260829T120000Z
```

To restore it:

1. Fully quit Codex Desktop.
2. Copy the selected backup over `~/.codex/config.toml`.
3. Ensure the restored file has mode `0600`.
4. Reopen Codex and run a status check.

Example:

```bash
cp "$HOME/.codex/config.toml.bak.<timestamp>" "$HOME/.codex/config.toml"
chmod 600 "$HOME/.codex/config.toml"
```

The plugin does not roll back or alter CLIProxyAPI account configuration because it never owns it.

## 10. Uninstall

Remove the plugin:

```bash
codex plugin remove cliproxy-models@cliproxy
```

Optionally remove the marketplace:

```bash
codex plugin marketplace remove cliproxy
```

Plugin removal does not automatically delete provider/profile entries already written to `~/.codex/config.toml`. Restore a pre-install backup or remove only the managed CLIProxyAPI block while Codex is fully closed.

## 11. Troubleshooting

### `CLIPROXY_API_KEY` is unset

Reload the environment without printing the value:

```bash
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
test -n "${CLIPROXY_API_KEY:-}" && echo "CLIPROXY_API_KEY is set"
```

### HTTP 401 or 403

Confirm the key file is current and the Codex process inherited `CLIPROXY_API_KEY`. Do not print the key while diagnosing.

### Exact model alias is absent

Inspect only model IDs from CLIProxyAPI and add stable aliases for exact Grok 4.6 and Gemini 3.7 Flash. The plugin will not substitute another version.

### Multiple possible aliases

Pass explicit `--grok-model` and `--gemini-model` IDs as shown in section 7, or simplify the aliases exported by CLIProxyAPI.

### Plain HTTP endpoint rejected

Use loopback HTTP or change the endpoint to HTTPS.

### Current Codex model is not published by CLIProxyAPI

Run setup with an explicit default (`grok` or `gemini`) or use the installer’s profiles-only mode from a checkout.

### Codex still shows the previous model

Fully quit all Codex Desktop processes and reopen the app. Existing threads can retain their original model/provider; create a new thread after switching.

## 12. Development checkout

Clone and validate:

```bash
git clone https://github.com/vai8havchoudhary/codex.git
cd codex

python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m unittest discover -s plugins/cliproxy-models/scripts -p 'test_*.py' -v
python3 -m compileall -q plugins/cliproxy-models/scripts tests
```

Use offline catalog fixtures for deterministic installer development; do not use real secret values in fixtures.
