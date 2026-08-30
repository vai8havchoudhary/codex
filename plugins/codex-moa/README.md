# Codex MoA

`codex-moa` is a native Codex plugin for long-horizon coding with model-diverse councils. It uses Codex subagents and the exact Grok 4.6 and Gemini 3.7 Flash models admitted by `cliproxy-models`.

It does **not** require Hermes Agent and does not introduce another agent runtime.

## Architecture

- Codex is the sole orchestration and execution runtime.
- The root thread is the coordinator and default single writer.
- Opposite-model agents localize, challenge plans, analyze concrete failures, and independently review the final diff.
- A bundled MCP server stores compact immutable checkpoint records under `CODEX_HOME`.
- CLIProxyAPI remains authoritative for upstream accounts, OAuth, credentials, quotas, retries, health, and failover.
- `cliproxy-models` remains the single model-admission authority; `codex-moa` imports its catalog and endpoint contracts rather than duplicating them.

## Model-authority dependency contract

`authority.json` pins the exact compatible marketplace bundle, consumer plugin, and model-authority plugin:

```text
cliproxy-plugins 2.0.0
codex-moa 2.0.0
cliproxy-models 1.0.0
```

Preflight supports both real layouts:

```text
Source checkout:
  <repo>/plugins/codex-moa
  <repo>/plugins/cliproxy-models
  <repo>/release.json

Versioned Codex cache:
  <cache>/cliproxy/codex-moa/2.0.0
  <cache>/cliproxy/cliproxy-models/1.0.0
```

The source layout is accepted only when the repository `release.json` agrees with `authority.json`. The installed-cache layout selects only the exact pinned authority version. It never chooses the highest, newest, or first directory. Missing, incompatible, malformed, or multiply located compatible authorities fail with an actionable error.

No user home path is hardcoded. Discovery starts from the executing plugin root.

## Model preflight

From either the source plugin root or the installed versioned cache root:

```bash
python3 scripts/preflight.py \
  --grok-model grok-4.6 \
  --gemini-model gemini-3.7-flash-high \
  --json
```

The preflight loads `cliproxy-models/scripts/catalog.py` and `plugin.py` from the release-bound authority location and checks that the live catalogs agree with the installed Codex profiles.

VPS2 currently demonstrates an important fail-closed case: `grok-4.6` is available, while Gemini exports both `gemini-3.7-flash-high` and `gemini-3.7-flash-advisor` with no bare alias. Automatic setup must refuse that ambiguity. An explicit exact alias works only when present in both catalogs.

Configure the model profiles through the model plugin:

```text
@cliproxy-models Set up CLIProxyAPI models with --gemini-model gemini-3.7-flash-high.
```

In a source checkout, its direct entry point is:

```bash
python3 ../cliproxy-models/scripts/plugin.py \
  --gemini-model gemini-3.7-flash-high \
  setup grok
```

That relative command is source-checkout-only; installed plugins live in separate name/version cache directories. Never select `-high` or `-advisor` silently.

## Use in Codex

```text
@codex-moa Run this task with a Grok-led native council.
@codex-moa Run this task with a Gemini-led native council.
@codex-moa Resume checkpoint <handle>.
```

The complete policy is in `skills/codex-moa/SKILL.md`. Research mappings are in `references/long-horizon-research.md`.

## Checkpoint MCP server

The server exposes:

- `checkpoint_validate`
- `checkpoint_put`
- `checkpoint_get`
- `checkpoint_list`

Checkpoint records are schema-validated, immutable, atomically written, mode `0600`, stored beneath a mode-`0700` directory, and addressed by opaque handles. The server receives only `CODEX_HOME`; it does not receive `CLIPROXY_API_KEY`.

## Troubleshooting authority location

When preflight reports that the exact model authority is missing, upgrade the marketplace and reinstall the model plugin:

```bash
codex plugin marketplace upgrade cliproxy
codex plugin add cliproxy-models@cliproxy
```

Then confirm the installed cache contains the exact version pinned by `authority.json`. Do not copy scripts between version directories and do not point preflight at an arbitrary installed version.

## Direct validation

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m compileall -q scripts mcp tests
python3 -m json.tool .codex-plugin/plugin.json >/dev/null
python3 -m json.tool .mcp.json >/dev/null
python3 -m json.tool authority.json >/dev/null
```
