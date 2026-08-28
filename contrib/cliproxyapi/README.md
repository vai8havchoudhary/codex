# CLIProxyAPI models in Codex Desktop

This integration exposes **Grok 4.6** and **Gemini 3.7 Flash** in Codex Desktop through one CLIProxyAPI model provider. CLIProxyAPI remains authoritative for all upstream accounts, credentials, quota balancing, health, and failover; Codex stores no upstream account list or secret value.

## Apply

Start CLIProxyAPI, quit Codex Desktop, then run:

```bash
cd contrib/cliproxyapi
./apply.command
```

The installer validates both catalog contracts that Codex depends on:

- `GET /v1/models`
- `GET /v1/models?client_version=...`

It admits only aliases that appear in both catalogs, resolves exact Grok 4.6 and Gemini 3.7 Flash versions, creates one `cliproxyapi` provider plus two profiles, writes `~/.codex/config.toml` atomically with mode `0600`, and creates a timestamped backup only when bytes change.

Profiles:

```text
cliproxy-grok-4-6
cliproxy-gemini-3-7-flash
```

By default, CLIProxyAPI becomes the active Desktop catalog provider, while the current model is preserved only when CLIProxyAPI publishes it. Otherwise select a default explicitly:

```bash
./apply.command --default grok
./apply.command --default gemini
```

To install provider/profiles without changing the active Desktop provider:

```bash
./apply.command --profiles-only
```

## Authentication

CLIProxyAPI's default endpoint is `http://127.0.0.1:8317/v1`. Override it with `--base-url` or `CLIPROXY_BASE_URL`.

When the proxy requires an API key, pass only the environment-variable name:

```bash
export CLIPROXY_API_KEY='local-proxy-token'
./apply.command --api-key-env CLIPROXY_API_KEY
```

The token value is used only for live catalog requests and is never printed or written. A Codex Desktop process launched from Finder must inherit the named variable when the provider itself requires it for inference.

## Multiple accounts

Do not create a Codex provider per Grok or Gemini account. Keep every account in CLIProxyAPI and publish one stable alias per model family. If the proxy intentionally exports multiple matching aliases, select one explicitly:

```bash
./apply.command \
  --grok-model 'EXACT_GROK_4_6_ALIAS' \
  --gemini-model 'EXACT_GEMINI_3_7_FLASH_ALIAS'
```

Nearby versions such as `grok-4.60`, `grok-4.6.1`, `gemini-3.70-flash`, and marker-less `gemini-3.7` are refused.

## Switch the default

```bash
./use-grok.command
./use-gemini.command
```

Reopen Codex Desktop after applying or switching.

## Verify

```bash
python3 -m py_compile catalog.py config_edit.py install.py test_install.py
sh -n apply.command use-grok.command use-gemini.command
python3 -m unittest -v test_install.py
```

Offline validation requires saved responses for both catalog shapes:

```bash
python3 install.py \
  --models-response-file openai-models.json \
  --codex-models-response-file codex-models.json \
  --dry-run
```
