# CLIProxyAPI Plugins for Codex

[![validate](https://github.com/vai8havchoudhary/codex/actions/workflows/validate.yml/badge.svg)](https://github.com/vai8havchoudhary/codex/actions/workflows/validate.yml)

A standalone Codex plugin marketplace for using a multi-account CLIProxyAPI model pool in Codex and Hermes Agent.

| Plugin | Purpose |
|---|---|
| `cliproxy-models` | Add exact Grok 4.6 and Gemini 3.7 Flash profiles to Codex Desktop. |
| `hermes-moa` | Configure Hermes Agent Mixture-of-Agents presets where Grok and Gemini advise/act together. |

CLIProxyAPI remains authoritative for all upstream accounts, OAuth sessions, quota balancing, health checks, retries, and failover. Neither plugin copies upstream account identifiers or API-key values into application configuration.

Current marketplace release: **1.1.0**. See [CHANGELOG.md](CHANGELOG.md).

## Quick start

Prerequisites:

- Codex with the `codex plugin` marketplace commands.
- Python 3.11 or newer.
- CLIProxyAPI exporting exact Grok 4.6 and Gemini 3.7 Flash aliases.
- Hermes Agent only when installing `hermes-moa`.

Export the proxy contract in every environment that launches Codex or Hermes:

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Add the marketplace:

```bash
codex plugin marketplace add vai8havchoudhary/codex --ref main
```

Install either or both plugins:

```bash
codex plugin add cliproxy-models@cliproxy
codex plugin add hermes-moa@cliproxy
```

### Codex models

```text
@cliproxy-models Set up CLIProxyAPI models and use Grok 4.6 by default.
```

Profiles created:

```text
cliproxy-grok-4-6
cliproxy-gemini-3-7-flash
```

### Hermes Mixture of Agents

```text
@hermes-moa Set up Hermes MoA with Grok leading.
```

Presets created:

```text
cliproxy-grok-led     # Gemini advises; Grok acts
cliproxy-gemini-led   # Grok advises; Gemini acts
```

Inside Hermes, select a persistent preset or use the configured default for one request:

```text
/model cliproxy-grok-led --provider moa
/moa Review this change and propose the safest implementation.
```

## Shared safety properties

- Exact-version admission only; nearby, marker-less, absent, or ambiguous aliases are refused.
- An alias must appear in both CLIProxyAPI's OpenAI-compatible and Codex-compatible catalogs.
- Exactly one provider is configured per application; upstream accounts remain behind CLIProxyAPI.
- Plain HTTP is accepted only for localhost and loopback endpoints; remote endpoints require HTTPS.
- `CLIPROXY_API_KEY` values are never printed or persisted. Only the environment-variable name is stored.
- Existing foreign provider/profile/preset definitions are not overwritten without explicit `--force` authorization.
- Application config mutations are backed up, post-validated, byte-idempotent, and rolled back on partial failure.
- No plugin enumerates or modifies CLIProxyAPI account files.

## Documentation

- [SETUP.md](SETUP.md) — installation, verification, tuning, upgrades, rollback, and troubleshooting.
- [agent.md](agent.md) — architecture and operating handbook for implementation agents.
- [AGENTS.md](AGENTS.md) — mandatory repository instructions consumed by Codex.
- [CONTRIBUTING.md](CONTRIBUTING.md) — contribution and validation workflow.
- [SECURITY.md](SECURITY.md) — security model and vulnerability reporting.
- [docs/RELEASING.md](docs/RELEASING.md) — marketplace versioning, tagging, and release checklist.
- [CHANGELOG.md](CHANGELOG.md) — user-visible changes by marketplace version.

## Development validation

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
for suite in plugins/*/scripts; do
  python3 -m unittest discover -s "$suite" -p 'test_*.py' -v
done
python3 -m compileall -q plugins tests
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
for manifest in plugins/*/.codex-plugin/plugin.json; do
  python3 -m json.tool "$manifest" >/dev/null
done
git diff --check
```

## Repository history

The previous Codex source-fork tree remains recoverable through Git history and `archive/codex-upstream-20260828`. Current `main` is exclusively the `cliproxy` plugin marketplace.
