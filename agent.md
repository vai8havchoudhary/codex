# Agent handbook

This document is the implementation and release handbook for agents working on the `cliproxy` Codex marketplace.

## Mission

Expose exact CLIProxyAPI-backed Grok 4.6 and Gemini 3.7 Flash routes in two places without moving account authority out of CLIProxyAPI:

- `cliproxy-models`: Codex model profiles;
- `hermes-moa`: Hermes Agent Mixture-of-Agents presets.

The repository is a standalone marketplace rooted at `.agents/plugins/marketplace.json` and `plugins/`. It must not accumulate Codex core patches or a second MoA runtime.

## Authority boundaries

### CLIProxyAPI owns

- upstream accounts and OAuth/session credentials;
- account selection and load balancing;
- quota, health, retry, and failover policy;
- stable model aliases and the `/v1/models` catalogs.

### `cliproxy-models` owns

- endpoint/catalog/exact-alias admission;
- one Codex provider plus two profiles;
- transactional `~/.codex/config.toml` changes;
- status, setup, and model switching.

### `hermes-moa` owns

- Hermes executable/profile discovery;
- one Hermes provider named `cliproxy`;
- two built-in-MoA preset objects;
- transactional Hermes config changes through `hermes config set`;
- status, tuning, setup, activation, rollback, and post-validation.

### No plugin owns

- account discovery or account-specific routes;
- upstream secret material;
- CLIProxyAPI mutation;
- speculative fallback to nearby models;
- an independent multi-agent execution engine.

## Runtime contract

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Rules:

- Check key presence; never echo its value.
- Plain HTTP is loopback-only; remote endpoints require HTTPS.
- Normalize exactly one `/v1` suffix.
- Query `GET /v1/models` and `GET /v1/models?client_version=...`.
- Admit the same exact model ID only when it appears in both catalogs.
- Fail closed on absent, ambiguous, marker-less, or nearby versions.

## Hermes MoA design

Hermes' built-in `moa` provider treats each preset as a selectable model. References run first and advise; the aggregator is the acting model that writes the final answer and performs tool calls.

Owned route topology:

| Preset | Reference | Aggregator |
|---|---|---|
| `cliproxy-grok-led` | exact Gemini 3.7 Flash | exact Grok 4.6 |
| `cliproxy-gemini-led` | exact Grok 4.6 | exact Gemini 3.7 Flash |

Defaults:

- `reference_max_tokens: 600`;
- `max_tokens: 4096`;
- `fanout: user_turn`;
- `privacy_filter: display` unless an existing `full` policy is stronger;
- `enabled: true`.

The plugin writes structured provider/preset objects through Hermes' own config CLI. It merges unrelated object fields, recognizes its routes by provider custody, refuses foreign collisions unless `--force`, skips equal values, validates exact post-write values, and restores exact original bytes on failure.

## Repository map

| Path | Responsibility |
|---|---|
| `.agents/plugins/marketplace.json` | Marketplace entries and policies |
| `release.json` | Marketplace version and exact plugin-version map |
| `plugins/cliproxy-models/` | Codex model provider/profile plugin |
| `plugins/hermes-moa/` | Hermes built-in-MoA configuration plugin |
| `plugins/*/.codex-plugin/plugin.json` | Plugin version and UI metadata |
| `plugins/*/skills/` | Model-facing operating procedures |
| `plugins/*/scripts/` | Standard-library implementation and tests |
| `SETUP.md` | User operations |
| `docs/RELEASING.md` | Release transaction |
| `tests/` | Marketplace and release contracts |

## Mutation requirements

Every write path must:

1. validate endpoint, environment, catalogs, and exact aliases first;
2. detect foreign ownership before mutation;
3. snapshot exact original bytes;
4. use the target application's supported config surface;
5. suppress/redact secret values in subprocess output;
6. post-validate requested values;
7. roll back exact bytes or remove a new partial file on failure;
8. write a mode-`0600` timestamped backup only after a successful changed transaction;
9. perform no write when already equal.

## Validation

Run the root test suite, every plugin script suite, Python compilation, JSON validation, and `git diff --check`. The Hermes suite uses a synthetic CLIProxy catalog and a fake Hermes executable; it proves real subprocess boundaries and exact rollback without needing user credentials.

A live Hermes/CLIProxyAPI smoke gate is valuable but must be reported as unavailable when it was not executed.

## Release discipline

`release.json` is authoritative for the marketplace tag. Each mapped version must equal the corresponding plugin manifest. `CHANGELOG.md` must contain a dated marketplace version section. Release only from exact green `main`, using either an annotated `v<version>` tag or guarded `release/v<version>` branch. See `docs/RELEASING.md`.
