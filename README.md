# CLIProxyAPI Models for Codex

[![validate](https://github.com/vai8havchoudhary/codex/actions/workflows/validate.yml/badge.svg)](https://github.com/vai8havchoudhary/codex/actions/workflows/validate.yml)

A standalone Codex plugin marketplace that adds exact **Grok 4.6** and **Gemini 3.7 Flash** profiles through one CLIProxyAPI model provider.

CLIProxyAPI remains authoritative for upstream accounts, OAuth sessions, quota balancing, health checks, retries, and failover. Codex receives one endpoint and stable aliases; this plugin never copies account identifiers or API-key values into `~/.codex/config.toml`.

Current release line: **1.0.x**. See [CHANGELOG.md](CHANGELOG.md).

## Quick start

Prerequisites:

- Codex with the `codex plugin` marketplace commands.
- Python 3.11 or newer.
- CLIProxyAPI running and exporting exact Grok 4.6 and Gemini 3.7 Flash aliases.

Export the local proxy contract in the environment that launches Codex:

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Add this repository as a marketplace and install the plugin:

```bash
codex plugin marketplace add vai8havchoudhary/codex --ref main
codex plugin add cliproxy-models@cliproxy
```

Start a new Codex session, then ask:

```text
@cliproxy-models Set up CLIProxyAPI models and use Grok 4.6 by default.
```

For Gemini:

```text
@cliproxy-models Set up CLIProxyAPI models and use Gemini 3.7 Flash by default.
```

Fully quit and reopen Codex Desktop after setup or model switching.

The complete installation, upgrade, rollback, and troubleshooting guide is in [SETUP.md](SETUP.md).

## Model profiles

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

## Documentation

- [SETUP.md](SETUP.md) — installation, verification, upgrades, rollback, and troubleshooting.
- [agent.md](agent.md) — architecture and operating handbook for implementation agents.
- [AGENTS.md](AGENTS.md) — mandatory repository instructions consumed by Codex.
- [CONTRIBUTING.md](CONTRIBUTING.md) — contribution and validation workflow.
- [SECURITY.md](SECURITY.md) — security model and vulnerability reporting.
- [docs/RELEASING.md](docs/RELEASING.md) — versioning, tagging, and release checklist.
- [CHANGELOG.md](CHANGELOG.md) — user-visible changes by version.

## Development validation

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m unittest discover -s plugins/cliproxy-models/scripts -p 'test_*.py' -v
python3 -m compileall -q plugins/cliproxy-models/scripts tests
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 -m json.tool plugins/cliproxy-models/.codex-plugin/plugin.json >/dev/null
```

## Repository history

The previous Codex source-fork tree remains recoverable through Git history and the `archive/codex-upstream-20260828` branch. The current `main` branch is exclusively this plugin marketplace.
