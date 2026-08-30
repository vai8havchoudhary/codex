# Setup and operations

This marketplace installs two native Codex plugins: `cliproxy-models` and `codex-moa`.

## Prerequisites

- Codex with plugin marketplace support.
- Python 3.11 or newer.
- CLIProxyAPI reachable from the environment that launches Codex.
- Exact Grok 4.6 and an explicitly selected Gemini 3.7 Flash alias exported in both CLIProxyAPI catalog views.

No Hermes Agent installation is required or supported by `codex-moa`.

## 1. Export the proxy contract

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Do not paste the key into Codex configuration or plugin arguments. The model plugin stores only:

```toml
env_key = "CLIPROXY_API_KEY"
```

A Codex Desktop process launched outside this environment may not inherit the variables. Configure the application launch environment and then fully restart Codex.

## 2. Add the marketplace

```bash
codex plugin marketplace add vai8havchoudhary/codex --ref main
```

For an existing installation:

```bash
codex plugin marketplace upgrade cliproxy
```

## 3. Install both native plugins

```bash
codex plugin add cliproxy-models@cliproxy
codex plugin add codex-moa@cliproxy
```

Remove the obsolete Hermes-dependent plugin when upgrading from marketplace 1.1.x:

```bash
codex plugin remove hermes-moa@cliproxy
```

## 4. Select the exact Gemini alias

VPS2 currently exports:

```text
grok-4.6
gemini-3.7-flash-high
gemini-3.7-flash-advisor
```

Because there is no bare `gemini-3.7-flash` and two exact family/version/marker candidates exist, Automatic setup must refuse this ambiguity. The resulting error is intentional.

Choose one explicit exact ID after deciding which route you want. Example using `-high`:

```text
@cliproxy-models Set up CLIProxyAPI models with --gemini-model gemini-3.7-flash-high and use Grok by default.
```

Equivalent direct entry point from the plugin directory:

```bash
python3 scripts/plugin.py \
  --gemini-model gemini-3.7-flash-high \
  setup grok
```

An explicit alias is accepted only when it is present in both:

```text
GET /v1/models
GET /v1/models?client_version=999.0.0
```

Do not infer that `-high` or `-advisor` is preferable from the name. The plugin performs admission, not account-policy selection.

## 5. Verify model setup

```text
@cliproxy-models Check my CLIProxyAPI model setup using --gemini-model gemini-3.7-flash-high.
```

The managed Codex profiles are:

```text
cliproxy-grok-4-6
cliproxy-gemini-3-7-flash
```

The Gemini profile name is stable even when its exact admitted model ID is `gemini-3.7-flash-high` or another explicitly selected exact alias.

## 6. Verify native council preflight

From the installed `codex-moa` plugin root:

```bash
python3 scripts/preflight.py \
  --gemini-model gemini-3.7-flash-high \
  --json
```

This reuses the sibling model plugin's catalog authority and verifies that the live exact IDs equal the installed Codex profiles. It performs no write.

## 7. Run a native long-horizon council

Grok-led:

```text
@codex-moa Run this task with a Grok-led native council. Localize first, maintain one writer, checkpoint validated milestones, and require independent final review.
```

Gemini-led:

```text
@codex-moa Run this task with a Gemini-led native council. Use Grok for independent criticism, failure analysis, and final review.
```

The plugin uses Codex's own subagent tools. It does not start Hermes or a separate scheduler.

## 8. Resume

```text
@codex-moa Resume checkpoint <opaque-handle>.
```

Resume first reconciles the live repository, branch, worktree, task authority, exact model admission, and the last validated milestone. A checkpoint is not permission to trust stale source state.

## 9. Check checkpoint status

```text
@codex-moa Show status for run <run-id>.
```

The checkpoint MCP server stores immutable JSON records beneath:

```text
${CODEX_HOME:-$HOME/.codex}/codex-moa/checkpoints
```

The directory is mode `0700`; records are mode `0600`. The server receives only `CODEX_HOME` and rejects sensitive field names and common secret-value patterns.

## Upgrade

```bash
codex plugin marketplace upgrade cliproxy
```

Then reinstall or upgrade both plugins using the Codex plugin UI/CLI and restart Codex Desktop. Re-run exact model preflight because available proxy aliases may have changed.

## Rollback

Model setup creates timestamped backups of `~/.codex/config.toml` when bytes change. Quit Codex, restore the intended backup, and restart.

For a bad marketplace release, install a known release ref rather than moving a published tag. Do not copy checkpoint records into Codex configuration.

## Uninstall

```bash
codex plugin remove codex-moa@cliproxy
codex plugin remove cliproxy-models@cliproxy
```

Removing `codex-moa` does not delete checkpoint records automatically. Review and remove `${CODEX_HOME:-$HOME/.codex}/codex-moa` manually only when you no longer need resume evidence.

## Troubleshooting

### Automatic Gemini setup says multiple aliases

Expected for the current VPS2 `-high` and `-advisor` catalog. Pass one exact `--gemini-model` value that exists in both catalogs.

### Explicit alias is not present in both catalogs

Do not bypass the check. Inspect CLIProxyAPI's two model catalog responses and correct the proxy/export configuration or choose a common exact alias.

### Native council preflight disagrees with the profile

Re-run `cliproxy-models` setup with the same exact explicit alias, then fully restart Codex and rerun preflight.

### Checkpoint server is unavailable

Confirm the plugin is installed, `python3` is available, `.mcp.json` is present, and `CODEX_HOME` is writable. Do not redirect the server to proxy account directories.

### A council repeats failures

The policy allows at most two coherent recovery rounds per blocker. Record a blocked checkpoint with exact evidence instead of continuing an unbounded loop.
