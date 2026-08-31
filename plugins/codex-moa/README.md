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

## Named councils

- `codex --profile luna-grok`: exact Luna root, Grok advisor/reviewer.
- `codex --profile grok-gemini`: Grok root, Gemini Flash High advisor/reviewer.

The matching `luna-grok` and `grok-gemini` skills/commands route to one shared policy. They do not change the active root model or grant broader write permissions. Gemini-led is unsupported; historical records are readable only. Named profile instructions apply leader duties only to the root, not its read-only children.

## Profile-aware preflight

```bash
python3 scripts/preflight.py --council luna-grok --leader-model gpt-5.6-luna \
  --grok-model grok-4.6 \
  --gemini-model gemini-3.7-flash-high \
  --json
```

Preflight validates:

- the live exact aliases through `cliproxy-models`;
- the shared provider in `~/.codex/config.toml`;
- `~/.codex/cliproxy-grok-4-6.config.toml`;
- `~/.codex/cliproxy-gemini-3-7-flash.config.toml`;
- the Luna model overlay and selected named council overlay/instructions;
- matching provider/model identities across all documents.

It refuses missing/malformed/symlink overlays, provider or model mismatches, and any legacy top-level `profile` selector or `[profiles.*]` table.

The current VPS2 catalog exposes both `gemini-3.7-flash-high` and `gemini-3.7-flash-advisor`; automatic resolution must fail and an explicit common alias must be used.

## Native council policy

- configuration admission alone does not prove native delegation; establish two actual opposite-model responses before writing;
- reserve one independent final reviewer and reuse the localizer for plan criticism;
- root thread coordinates and is the default single writer;
- opposite-model agents localize, critique plans, analyze concrete failures, and independently review;
- repository-native validation is authoritative;
- recovery is bounded to two coherent rounds per blocker;
- the bundled MCP stores compact immutable checkpoints only and receives only `CODEX_HOME`.

New schema-2 completion requires exact council/model identity, actual-shaped native agent witness fields, a returned final review approval and passing repository gates. These are model-submitted claims, not cryptographic attestation: independently verify native runtime events. Schema-1 checkpoint digests and read access remain compatible; new writes/resumption require a new schema-2 run.

See `skills/codex-moa/SKILL.md` and `references/long-horizon-research.md`.

Named profiles pin the transaction-managed live-derived `model_catalog_json` snapshot so native subagent selection does not depend on a subsequently replaced shared cache. Preflight rejects mismatched pointers, unsafe/unmanaged files, and stale metadata. It still cannot prove a native agent will execute; actual spawn/response evidence is required.
