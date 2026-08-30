# Codex MoA

`codex-moa` 2.0.0 is a native Codex plugin for long-horizon coding with model-diverse councils. Codex remains the only orchestration runtime; CLIProxyAPI remains the only upstream account/credential/routing authority.

## Model-authority contract

`authority.json` pins:

```text
cliproxy-plugins 2.0.0
codex-moa 2.0.0
cliproxy-models 1.1.0
```

Source checkout:

```text
<repo>/plugins/codex-moa
<repo>/plugins/cliproxy-models
<repo>/release.json
```

Installed versioned cache:

```text
<cache>/cliproxy/codex-moa/2.0.0
<cache>/cliproxy/cliproxy-models/1.1.0
```

Preflight selects only the exact pinned authority. It never chooses the latest or first cached version and never hardcodes a home path.

## Profile-aware preflight

```bash
python3 scripts/preflight.py \
  --grok-model grok-4.6 \
  --gemini-model gemini-3.7-flash-high \
  --json
```

Preflight validates:

- the live exact aliases through `cliproxy-models`;
- the shared provider in `~/.codex/config.toml`;
- `~/.codex/cliproxy-grok-4-6.config.toml`;
- `~/.codex/cliproxy-gemini-3-7-flash.config.toml`;
- matching provider/model identities across all documents.

It refuses missing/malformed/symlink overlays, provider or model mismatches, and any legacy top-level `profile` selector or `[profiles.*]` table.

The current VPS2 catalog exposes both `gemini-3.7-flash-high` and `gemini-3.7-flash-advisor`; automatic resolution must fail and an explicit common alias must be used.

## Native council policy

- root thread coordinates and is the default single writer;
- opposite-model agents localize, critique plans, analyze concrete failures, and independently review;
- repository-native validation is authoritative;
- recovery is bounded to two coherent rounds per blocker;
- the bundled MCP stores compact immutable checkpoints only and receives only `CODEX_HOME`.

See `skills/codex-moa/SKILL.md` and `references/long-horizon-research.md`.
