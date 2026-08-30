# CLIProxyAPI native plugins for Codex

[![validate](https://github.com/vai8havchoudhary/codex/actions/workflows/validate.yml/badge.svg)](https://github.com/vai8havchoudhary/codex/actions/workflows/validate.yml)

A native Codex plugin marketplace for using multiple CLIProxyAPI-backed models safely in Codex Desktop and for coordinating long-horizon coding work through Codex's own subagent runtime.

The marketplace contains exactly two plugins:

| Plugin | Purpose |
|---|---|
| `cliproxy-models` | Admit exact Grok 4.6 and Gemini 3.7 Flash aliases and install one shared CLIProxyAPI provider plus two Codex profiles. |
| `codex-moa` | Run bounded, model-diverse long-horizon coding councils using native Codex agents, skills, commands, and an immutable checkpoint MCP server. |

Neither plugin requires Hermes Agent. There is no alternate orchestration runtime. CLIProxyAPI remains the sole authority for upstream accounts, OAuth sessions, credentials, quotas, retries, health checks, and failover.

Current marketplace release line: **2.0.x**.

## Environment

Export the local proxy contract in the environment that launches Codex:

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

The plugins never enumerate proxy account files and never print or persist the key value. Codex configuration stores only the environment-variable name `CLIPROXY_API_KEY`.

## Install

```bash
codex plugin marketplace add vai8havchoudhary/codex --ref main
codex plugin add cliproxy-models@cliproxy
codex plugin add codex-moa@cliproxy
```

Set up the model profiles first:

```text
@cliproxy-models Set up CLIProxyAPI models.
```

Then run a native council:

```text
@codex-moa Run this repository task with a Grok-led native council.
```

or:

```text
@codex-moa Run this repository task with a Gemini-led native council.
```

Fully quit and reopen Codex Desktop after marketplace or provider changes.

## VPS2 Gemini ambiguity

The authoritative VPS2 catalog currently demonstrates this shape:

```text
grok-4.6
gemini-3.7-flash-high
gemini-3.7-flash-advisor
```

There is no bare `gemini-3.7-flash`. Automatic setup must refuse because two exact Gemini 3.7 Flash aliases are present. Select one exact alias explicitly, for example:

```text
@cliproxy-models Set up with --gemini-model gemini-3.7-flash-high.
```

The explicit alias is accepted only when it appears in both CLIProxyAPI catalog views. The plugin never infers account policy from alias names.

## Long-horizon policy

`codex-moa` uses:

- repository localization before editing;
- one accepted dependency-aware plan;
- one acting writer by default;
- opposite-model criticism and review at high-leverage gates;
- repository-native validation as the source of truth;
- bounded failure recovery and explicit stop conditions;
- compact immutable checkpoints addressed by opaque handles;
- fresh repository reconciliation when resuming.

See [`plugins/codex-moa/skills/codex-moa/SKILL.md`](plugins/codex-moa/skills/codex-moa/SKILL.md) and [`plugins/codex-moa/references/long-horizon-research.md`](plugins/codex-moa/references/long-horizon-research.md).

## Safety properties

- Exact-version admission in both CLIProxyAPI catalogs.
- Ambiguous, nearby, malformed, or marker-less aliases are refused.
- Plain HTTP is accepted only for loopback endpoints; remote endpoints require HTTPS.
- Exactly one Codex provider fronts all proxy-managed accounts.
- No API-key value or account metadata is persisted.
- Codex configuration writes are atomic, mode `0600`, backed up, post-validated, and byte-idempotent.
- MoA checkpoints reject sensitive fields and common secret-value patterns.
- The checkpoint server receives only `CODEX_HOME`; it cannot route models or execute code.
- Councils use native Codex subagents and bounded repair budgets.

## Documentation

- [SETUP.md](SETUP.md) — installation, exact alias selection, verification, upgrade, rollback, and uninstall.
- [AGENTS.md](AGENTS.md) — mandatory repository invariants for Codex.
- [agent.md](agent.md) — architecture and maintainer handbook.
- [CONTRIBUTING.md](CONTRIBUTING.md) — development and pull-request contract.
- [SECURITY.md](SECURITY.md) — security model and reporting.
- [docs/RELEASING.md](docs/RELEASING.md) — guarded release process.
- [CHANGELOG.md](CHANGELOG.md) — versioned user-visible changes.

## Development validation

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
for suite in plugins/*/scripts plugins/*/tests; do
  if compgen -G "$suite/test_*.py" >/dev/null; then
    python3 -m unittest discover -s "$suite" -p 'test_*.py' -v
  fi
done
python3 -m compileall -q plugins tests
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 -m json.tool release.json >/dev/null
for manifest in plugins/*/.codex-plugin/plugin.json; do
  python3 -m json.tool "$manifest" >/dev/null
done
for mcp in plugins/*/.mcp.json; do
  [ -e "$mcp" ] || continue
  python3 -m json.tool "$mcp" >/dev/null
done
git diff --check
```
