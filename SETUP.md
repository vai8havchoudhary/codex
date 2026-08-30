# Setup and operations

This marketplace installs `cliproxy-models` 1.1.0 and `codex-moa` 2.0.0 under marketplace bundle 2.0.0.

## Prerequisites

- Codex CLI/Desktop with plugin marketplace support and the modern profile-file contract.
- Python 3.11 or newer.
- CLIProxyAPI reachable from the process that launches Codex.
- Exact Grok 4.6 and an explicitly selected Gemini 3.7 Flash alias present in both catalog views.

## 1. Export the proxy contract

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Never paste the key into TOML or plugin arguments. Only `env_key = "CLIPROXY_API_KEY"` is persisted.

## 2. Install or upgrade

```bash
codex plugin marketplace add vai8havchoudhary/codex --ref main
# Existing marketplace:
codex plugin marketplace upgrade cliproxy

codex plugin add cliproxy-models@cliproxy
codex plugin add codex-moa@cliproxy
```

Expected versioned cache shape:

```text
<CODEX_HOME>/plugins/cache/cliproxy/cliproxy-models/1.1.0
<CODEX_HOME>/plugins/cache/cliproxy/codex-moa/2.0.0
```

No user home path is hardcoded. Remove obsolete `hermes-moa@cliproxy` when upgrading from 1.1.x.

## 3. Select the exact Gemini alias

VPS2 exports `grok-4.6`, `gemini-3.7-flash-high`, and `gemini-3.7-flash-advisor`, but no bare Gemini alias. Automatic setup must refuse the two matching Gemini routes.

Example explicit setup:

```bash
python3 <installed-cliproxy-models-root>/scripts/plugin.py \
  --gemini-model gemini-3.7-flash-high \
  setup grok
```

The explicit ID is accepted only when returned by both:

```text
GET /v1/models
GET /v1/models?client_version=999.0.0
```

## 4. Three-file profile transaction

Setup maintains exactly:

```text
BASE    ~/.codex/config.toml
GROK    ~/.codex/cliproxy-grok-4-6.config.toml
GEMINI  ~/.codex/cliproxy-gemini-3-7-flash.config.toml
```

The base file contains one provider plus the selected default model/provider. The two overlays contain top-level values like:

```toml
model = "grok-4.6"
model_provider = "cliproxyapi"
```

There must be no managed top-level `profile` selector and no managed `[profiles.*]` table in `config.toml`.

### Migration policy

- A legacy selector equal to one of this plugin's profile names is removed.
- Legacy tables are migrated only when enclosed by the plugin's exact managed markers.
- Unmanaged selectors/tables, malformed marker regions, user-owned top-level `model`/`model_provider` collisions in overlay files, symlinks, and non-regular files fail closed.
- Unrelated TOML and comments are preserved when ownership is unambiguous.

### Transaction properties

Before writing, setup snapshots all three paths and verifies they have not changed concurrently. Every changed existing file receives a timestamped mode-`0600` backup. Temporary files are fsynced and atomically replaced; all three final documents are reparsed and cross-validated. Any failure restores exact original bytes/modes and removes newly created partial files and transaction backups. An equal re-run writes nothing and creates no backup.

## 5. Verify profile execution

After fully restarting Codex:

```bash
codex exec --profile cliproxy-grok-4-6 'Reply with GROK_PROFILE_OK'
codex exec --profile cliproxy-gemini-3-7-flash 'Reply with GEMINI_PROFILE_OK'
```

Both commands should load the base provider and then their separate overlay file.

## 6. Verify native council preflight

From installed `codex-moa` 2.0.0:

```bash
python3 scripts/preflight.py \
  --grok-model grok-4.6 \
  --gemini-model gemini-3.7-flash-high \
  --json
```

`authority.json` pins `cliproxy-models` 1.1.0. Preflight verifies the base provider and both modern profile overlay files. Missing files, legacy base profiles, mismatched providers/models, unsafe paths, or the wrong installed authority version are actionable failures.

## 7. Run or resume a native council

```text
@codex-moa Run this task with a Grok-led native council.
@codex-moa Run this task with a Gemini-led native council.
@codex-moa Resume checkpoint <opaque-handle>.
```

The checkpoint server stores immutable JSON beneath `${CODEX_HOME:-$HOME/.codex}/codex-moa/checkpoints` with directory mode `0700` and file mode `0600`. It receives only `CODEX_HOME`.

## Rollback

Quit Codex. Restore the intended coordinated `*.bak.<timestamp>` copies for the base and any pre-existing overlays, or remove overlays that did not exist before the transaction. Restart Codex and re-run setup/preflight. The installer itself performs this rollback automatically when its transaction fails.

## Troubleshooting

### `--profile` reports legacy profile configuration

Upgrade/reinstall `cliproxy-models` 1.1.0 and rerun setup. Do not manually recreate `[profiles.*]`; current Codex expects `<profile>.config.toml` overlays.

### Automatic Gemini setup reports ambiguity

Expected for the VPS2 `-high` / `-advisor` catalog. Pass one exact common alias explicitly.

### Preflight cannot locate model authority

Ensure the exact cache directories exist:

```text
cliproxy-models/1.1.0
codex-moa/2.0.0
```

Then upgrade the marketplace and reinstall the model plugin. Preflight never guesses another version.

### Preflight reports a missing or mismatched overlay

Rerun the exact same explicit model setup, fully restart Codex, and retry preflight. Do not bypass the mismatch.

See [`docs/VPS2_GATE_2026-08-30.md`](docs/VPS2_GATE_2026-08-30.md) for the prior exact-main evidence and why a fresh post-correction gate is still required.
