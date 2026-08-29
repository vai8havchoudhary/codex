# Agent handbook

This document is the implementation and release handbook for agents working on the CLIProxyAPI Models plugin.

## Mission

Expose exact CLIProxyAPI-backed Grok 4.6 and Gemini 3.7 Flash profiles in Codex while keeping all upstream account and credential authority inside CLIProxyAPI.

The repository is a standalone Codex marketplace:

```text
.agents/plugins/marketplace.json
plugins/cliproxy-models/
```

It is not a Codex application fork and must not accumulate Codex core patches.

## Authority boundaries

### CLIProxyAPI owns

- upstream Grok and Gemini accounts;
- OAuth and session credentials;
- account selection and load balancing;
- quota, health, retry, and failover policy;
- the model catalogs served at `/v1/models`.

### The plugin owns

- validating the provider endpoint;
- validating both the OpenAI-compatible and Codex-compatible model catalogs;
- selecting exact stable aliases;
- adding one `cliproxyapi` provider and two Codex profiles;
- preserving and atomically updating `~/.codex/config.toml`;
- status, setup, and default-model switching workflows.

### The plugin must never own

- account discovery;
- account-specific routes or providers;
- upstream secret material;
- CLIProxyAPI configuration mutation;
- speculative fallback to nearby model versions.

## Repository map

| Path | Responsibility |
|---|---|
| `.agents/plugins/marketplace.json` | Marketplace identity, source path, install and auth policy |
| `plugins/cliproxy-models/.codex-plugin/plugin.json` | Plugin version and Codex UI metadata |
| `plugins/cliproxy-models/skills/cliproxy-models/SKILL.md` | Model-facing operating procedure and security rules |
| `plugins/cliproxy-models/scripts/plugin.py` | Stable status/setup/use entry point |
| `plugins/cliproxy-models/scripts/catalog.py` | Endpoint, catalog, provider, and exact-alias admission |
| `plugins/cliproxy-models/scripts/config_edit.py` | Comment-preserving TOML rendering and atomic writes |
| `plugins/cliproxy-models/scripts/install.py` | Transactional installer |
| `plugins/cliproxy-models/commands/` | Codex slash-command guidance |
| `SETUP.md` | User installation, upgrade, rollback, and troubleshooting |
| `docs/RELEASING.md` | Maintainer release procedure |
| `tests/` | Marketplace, documentation, and release-contract tests |

## Runtime contract

The supported launch environment is:

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Rules:

- Check whether `CLIPROXY_API_KEY` is set; never echo its value.
- Accept plaintext HTTP only for `localhost`, `127.0.0.1`, or `::1`.
- Normalize the provider base URL to exactly one `/v1` suffix.
- Query both catalog shapes:
  - OpenAI-compatible: `GET /v1/models`
  - Codex-compatible: `GET /v1/models?client_version=...`
- Admit an alias only when the same exact ID appears in both catalogs.
- Fail closed on absent, ambiguous, marker-less, or nearby versions.
- Store only `env_key = "CLIPROXY_API_KEY"` in Codex configuration.

## Required behavioral invariants

1. One provider, regardless of upstream account count.
2. Exact Grok 4.6 and Gemini 3.7 Flash only.
3. No secret values in source, output, config, backups, fixtures, or release artifacts.
4. Existing unrelated providers are never repurposed.
5. Existing CLIProxyAPI providers are reused only when their identity is unambiguous.
6. Managed profiles are deterministic:
   - `cliproxy-grok-4-6`
   - `cliproxy-gemini-3-7-flash`
7. A failed preflight performs no configuration write.
8. A successful second application is byte-identical, byte-idempotent, and creates no new backup.
9. Changed writes are atomic, mode `0600`, and recoverable through a timestamped backup.
10. The plugin never reads or changes CLIProxyAPI account files.

## Implementation workflow

Before editing:

1. Read `AGENTS.md`, this file, `SETUP.md`, and the relevant production/test files.
2. Identify the authority boundary affected by the request.
3. State whether the change affects catalog admission, provider selection, TOML mutation, plugin UX, or release metadata.

While editing:

- Prefer standard-library Python and deterministic data structures.
- Keep error messages typed and actionable without exposing secrets.
- Preserve the single entry point in `scripts/plugin.py`.
- Do not add a second installer, second provider registry, or shell-only mutation path.
- Add regression coverage for every new refusal or mutation rule.

After editing:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m unittest discover -s plugins/cliproxy-models/scripts -p 'test_*.py' -v
python3 -m compileall -q plugins/cliproxy-models/scripts tests
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 -m json.tool plugins/cliproxy-models/.codex-plugin/plugin.json >/dev/null
```

Report which gates actually ran and whether a live CLIProxyAPI/Codex Desktop smoke test was available.

## Release discipline

- The plugin manifest is the version authority.
- `CHANGELOG.md` must contain the same version and release date.
- Release tags use `v<semantic version>`.
- The tag-driven workflow must reject a tag that does not match the manifest.
- Release archives must contain no key files, caches, backups, or generated local configuration.
- Follow `docs/RELEASING.md`; do not create a tag or release unless explicitly requested.

## Definition of done

A change is done only when the repository invariants remain true, documentation matches the installed commands, focused tests cover the changed behavior, JSON and Python validation pass, and the resulting commit is identifiable.
