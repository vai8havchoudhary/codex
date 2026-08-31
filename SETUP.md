# Setup and operations

This marketplace installs `cliproxy-models` 1.1.0 and `codex-moa` 2.0.0 under marketplace bundle 2.0.0.

## Prerequisites

- Codex CLI/Desktop with plugin marketplace support and the modern profile-file contract.
- Python 3.11 or newer.
- CLIProxyAPI reachable from the process that launches Codex.
- Exact `gpt-5.6-luna` (not `gpt-5.6-luna-advisor`), Grok 4.6 and an explicitly selected Gemini 3.7 Flash alias present in both catalog views.

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

The seven-file two-council installation accepts only explicit `--gemini-model gemini-3.7-flash-high`. Requesting the Advisor alias is refused before mutation, even if it appears in both catalogs; setup does not silently substitute High. Pure catalog resolution can still identify other exact aliases, but they do not satisfy this installation contract.

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

## 4. Guarded seven-file profile transaction

Setup maintains exactly:

```text
BASE    ~/.codex/config.toml
GROK    ~/.codex/cliproxy-grok-4-6.config.toml
GEMINI  ~/.codex/cliproxy-gemini-3-7-flash.config.toml
LUNA    ~/.codex/cliproxy-luna.config.toml
COUNCIL ~/.codex/luna-grok.config.toml
COUNCIL ~/.codex/grok-gemini.config.toml
CATALOG ~/.codex/cliproxy-council-models.json
```

The base file contains one provider plus the selected default model/provider. The three model overlays contain top-level values like:

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

Before writing, setup snapshots all seven paths and verifies they have not changed concurrently. Every changed existing file receives a timestamped mode-`0600` backup. Temporary files are fsynced and atomically replaced; all seven final documents are reparsed and cross-validated. Any failure restores exact original bytes/modes and removes newly created partial files and transaction backups. An equal re-run writes nothing and creates no backup.

## 5. Verify profile execution

After fully restarting Codex:

```bash
codex exec --profile cliproxy-grok-4-6 'Reply with GROK_PROFILE_OK'
codex exec --profile cliproxy-luna 'Reply with LUNA_PROFILE_OK'
codex exec --profile cliproxy-gemini-3-7-flash 'Reply with GEMINI_PROFILE_OK'
```

The model commands should load the base provider and then their separate overlay file.

## 6. Verify native council preflight

From installed `codex-moa` 2.0.0:

```bash
python3 scripts/preflight.py \
  --grok-model grok-4.6 \
  --gemini-model gemini-3.7-flash-high \
  --json
```

`authority.json` pins `cliproxy-models` 1.1.0. Preflight verifies the base provider, three model overlays, and the selected named council overlay. Missing files, legacy base profiles, mismatched providers/models, unsafe paths, or the wrong installed authority version are actionable failures.

## 7. Run or resume a native council

Start `codex --profile luna-grok` or `codex --profile grok-gemini`. Each named overlay binds its exact leader and root-only shared-policy instruction. Children retain their assigned read-only role. A skill cannot switch the root model: mismatches stop. Gemini-led is unsupported. Run preflight with `--council luna-grok --leader-model gpt-5.6-luna` or `--council grok-gemini --leader-model grok-4.6` plus the explicit Gemini flag.

Preflight is configuration admission, not native delegation proof. Establish two opposite-model native agent responses before writing; reserve one for final review. After a long run, audit actual native spawn IDs, model overrides, returned final verdict, and final revision. Schema-2 checkpoint witness validation does not authenticate self-reported model claims; schema-1 records remain readable but cannot continue as new writes.


```text
$luna-grok Run this task with Luna writing and Grok reviewing.
$grok-gemini Run this task with Grok writing and Gemini High reviewing.
@codex-moa Resume checkpoint <opaque-handle>.
```

The checkpoint server stores immutable JSON beneath `${CODEX_HOME:-$HOME/.codex}/codex-moa/checkpoints` with directory mode `0700` and file mode `0600`. It receives only `CODEX_HOME`.

Standalone Luna default switching: `python3 <installed-cliproxy-models-root>/scripts/plugin.py --gemini-model gemini-3.7-flash-high use luna`. To repair profiles without changing an already admitted default, use the lower-level `install.py --default preserve` with the same explicit alias flags. Do not change a user's unrelated default during qualification.

## Rollback

Quit Codex. Restore the intended coordinated `*.bak.<timestamp>` copies for the base and any pre-existing overlays, or remove overlays that did not exist before the transaction. Restart Codex and re-run setup/preflight. The installer itself performs this rollback automatically when its transaction fails.

## Troubleshooting

### `--profile` reports legacy profile configuration

Upgrade/reinstall `cliproxy-models` 1.1.0 and rerun setup. Do not manually recreate `[profiles.*]`; current Codex expects `<profile>.config.toml` overlays.

### Automatic Gemini setup reports ambiguity

Expected for the VPS2 `-high` / `-advisor` catalog. Pass `--gemini-model gemini-3.7-flash-high` explicitly for the supported two-council installation; any other requested Gemini alias is refused before writing files.

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

## Stable native council catalog

Named council overlays own `model_catalog_json`, pointing at the transaction-managed `cliproxy-council-models.json` beside the base config. It contains the exact three admitted models with the original live Codex-catalog metadata; capabilities are never synthesized. The JSON ownership marker is `_codex_cliproxy_models: 1`. Unmanaged or malformed JSON, duplicates/missing models, unsafe paths, and concurrent changes fail closed. The seventh file shares backups, mode 0600, post-validation, idempotence and exact rollback with all six TOML documents.

This derived startup snapshot keeps native subagent model selection independent of mutable shared catalog-cache entries. It is not a second alias authority: preflight still reads both live proxy catalogs and refuses stale snapshot metadata. The base default is not pinned to this three-model snapshot, so an unrelated admitted default is preserved by `--default preserve`. Restart Codex after setup/catalog refresh.
