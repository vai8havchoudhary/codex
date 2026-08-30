# CLIProxyAPI Models plugin

`cliproxy-models` 1.1.0 is the single model-admission and Codex provider-configuration authority for this marketplace.

It validates exact Grok 4.6 and Gemini 3.7 Flash aliases in both CLIProxyAPI catalog views and configures one provider plus two modern Codex profile overlays:

```text
~/.codex/config.toml
~/.codex/cliproxy-grok-4-6.config.toml
~/.codex/cliproxy-gemini-3-7-flash.config.toml
```

The base file contains the shared provider and selected top-level default model/provider. Each profile file contains top-level `model` and `model_provider` keys. The plugin does not write a top-level `profile` selector or `[profiles.*]` tables.

## Required launch environment

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Only the environment-variable name is stored. The plugin never reads CLIProxyAPI account files or persists the key value.

## Setup

```bash
python3 scripts/plugin.py \
  --gemini-model gemini-3.7-flash-high \
  setup grok
```

The live VPS2 catalog currently contains `grok-4.6`, `gemini-3.7-flash-high`, and `gemini-3.7-flash-advisor`, with no bare Gemini alias. Automatic Gemini selection intentionally refuses this ambiguity; an explicit exact alias must exist in both catalogs.

## Safe migration and transaction

The installer recognizes and removes only its own legacy managed block. Unmanaged legacy selectors/tables or user-owned `model`/`model_provider` collisions fail closed.

All changed base/profile files are committed as one transaction:

- regular-file and symlink checks before mutation;
- timestamped mode-`0600` backups for changed existing files;
- atomic temporary-file replacement and directory sync;
- post-validation of the complete three-document state;
- exact byte/mode rollback if any write or validation fails;
- byte- and mode-idempotent reapplication with no new backups.

Unrelated TOML and comments are preserved where the ownership boundary is unambiguous.

See [SETUP.md](../../SETUP.md), [agent.md](../../agent.md), and [the VPS2 gate record](../../docs/VPS2_GATE_2026-08-30.md).
