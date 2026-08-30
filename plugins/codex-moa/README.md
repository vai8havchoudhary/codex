# Codex MoA

`codex-moa` is a native Codex plugin for long-horizon coding with model-diverse councils. It uses Codex subagents and the exact Grok 4.6 and Gemini 3.7 Flash models installed by the sibling `cliproxy-models` plugin.

It does **not** require Hermes Agent and does not introduce another agent runtime.

## Architecture

- Codex is the sole orchestration and execution runtime.
- The root thread is the coordinator and default single writer.
- Opposite-model agents localize, challenge plans, analyze concrete failures, and independently review the final diff.
- A bundled MCP server stores compact immutable checkpoint records under `CODEX_HOME`.
- CLIProxyAPI remains authoritative for upstream accounts, OAuth, credentials, quotas, retries, health, and failover.

## Model preflight

```bash
python3 scripts/preflight.py --json
```

The preflight reuses `cliproxy-models/scripts/catalog.py` as the single model-admission authority and checks that the live catalog agrees with the installed Codex profiles.

VPS2 currently demonstrates an important fail-closed case: `grok-4.6` is available, while Gemini may expose both `gemini-3.7-flash-high` and `gemini-3.7-flash-advisor` with no bare alias. Automatic setup must refuse that ambiguity. An explicit exact alias works when present in both catalogs:

```bash
python3 ../cliproxy-models/scripts/plugin.py \
  --gemini-model gemini-3.7-flash-high \
  setup grok
```

Never select `-high` or `-advisor` silently.

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

## Direct validation

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m compileall -q scripts mcp tests
python3 -m json.tool .codex-plugin/plugin.json >/dev/null
python3 -m json.tool .mcp.json >/dev/null
```
