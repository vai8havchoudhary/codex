# CLIProxyAPI native plugins for Codex

[![validate](https://github.com/vai8havchoudhary/codex/actions/workflows/validate.yml/badge.svg)](https://github.com/vai8havchoudhary/codex/actions/workflows/validate.yml)

A native Codex plugin marketplace for safely admitting multiple CLIProxyAPI-backed models and coordinating long-horizon coding through Codex's own subagent runtime.

| Plugin | Version in bundle 2.0.0 | Purpose |
|---|---:|---|
| `cliproxy-models` | 1.1.0 | Admit exact Grok 4.6 and Gemini 3.7 Flash IDs, configure one CLIProxyAPI provider, and maintain modern Codex profile overlay files. |
| `codex-moa` | 2.0.0 | Run bounded model-diverse councils with native Codex agents and immutable checkpoint MCP state. |

Neither plugin requires Hermes or introduces another orchestration runtime. CLIProxyAPI remains the sole authority for upstream accounts, OAuth sessions, credentials, quotas, health, retries, and failover.

## Environment and installation

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"

codex plugin marketplace add vai8havchoudhary/codex --ref main
codex plugin add cliproxy-models@cliproxy
codex plugin add codex-moa@cliproxy
```

The plugins never enumerate proxy account files and never print or persist the key value. Codex stores only the environment-variable name `CLIPROXY_API_KEY`.

## Modern Codex profiles

Codex 0.134.0 and later load the base configuration and then overlay a separate profile file. `cliproxy-models` 1.1.0 therefore maintains this three-document state:

```text
~/.codex/config.toml
~/.codex/cliproxy-grok-4-6.config.toml
~/.codex/cliproxy-gemini-3-7-flash.config.toml
```

The base file contains the single provider and selected top-level default `model` / `model_provider`. Each overlay contains top-level `model` and `model_provider`. The plugin removes only its own managed legacy tables and never leaves a managed top-level `profile` selector or `[profiles.*]` table.

All changed documents form one backup-aware, mode-`0600`, atomic, post-validated transaction. Any partial write or validation failure restores exact original bytes and modes. Unmanaged collisions, malformed files, and symlinks fail before mutation.

## Exact alias setup

The authoritative VPS2 catalog contains:

```text
grok-4.6
gemini-3.7-flash-high
gemini-3.7-flash-advisor
```

There is no bare `gemini-3.7-flash`. Automatic Gemini selection must refuse. Choose an exact ID only when it is present in both CLIProxyAPI catalogs:

```text
@cliproxy-models Set up CLIProxyAPI models with --gemini-model gemini-3.7-flash-high and use Grok by default.
```

Modern profile usage after setup:

```bash
codex exec --profile cliproxy-grok-4-6 'Reply with GROK_PROFILE_OK'
codex exec --profile cliproxy-gemini-3-7-flash 'Reply with GEMINI_PROFILE_OK'
```

## Packaged dependency contract

`codex-moa/authority.json` binds the consumer to `cliproxy-models` 1.1.0 in both supported layouts:

```text
<repo>/plugins/codex-moa + <repo>/plugins/cliproxy-models
<cache>/cliproxy/codex-moa/2.0.0 + <cache>/cliproxy/cliproxy-models/1.1.0
```

The native preflight reads the base provider and both sibling profile overlays. It selects only the exact pinned authority version and refuses missing, incompatible, malformed, or multiply located authorities.

## Native council

```text
@codex-moa Run this repository task with a Grok-led native council.
@codex-moa Run this repository task with a Gemini-led native council.
@codex-moa Resume checkpoint <handle>.
```

The policy uses repository localization, one accepted plan, one writer by default, opposite-model criticism at high-leverage gates, validation-led bounded recovery, independent final review, and compact immutable checkpoints.

## Evidence and release status

The pre-correction exact-main VPS2 provider/MCP/council evidence and the profile blocker are recorded in [`docs/VPS2_GATE_2026-08-30.md`](docs/VPS2_GATE_2026-08-30.md). That earlier PASS does not waive the need for a fresh exact-main reinstall/profile/council gate after this correction.

No `v2.0.0` release should be published until that final gate is adjudicated.

## Development validation

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
for suite in plugins/*/scripts plugins/*/tests; do
  if [[ -d "$suite" ]] && compgen -G "$suite/test_*.py" >/dev/null; then
    python3 -m unittest discover -s "$suite" -p 'test_*.py' -v
  fi
done
python3 -m compileall -q plugins tests
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 -m json.tool release.json >/dev/null
for manifest in plugins/*/.codex-plugin/plugin.json; do python3 -m json.tool "$manifest" >/dev/null; done
for contract in plugins/*/authority.json; do [[ -e "$contract" ]] || continue; python3 -m json.tool "$contract" >/dev/null; done
for mcp in plugins/*/.mcp.json; do [[ -e "$mcp" ]] || continue; python3 -m json.tool "$mcp" >/dev/null; done
git diff --check
```

See [SETUP.md](SETUP.md), [AGENTS.md](AGENTS.md), [agent.md](agent.md), [SECURITY.md](SECURITY.md), and [docs/RELEASING.md](docs/RELEASING.md).
