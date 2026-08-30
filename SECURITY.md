# Security policy

## Reporting

Do not open a public issue containing API keys, account identifiers, local configuration/profile contents, checkpoint contents, backup contents, or exploit details. Prefer a private GitHub security advisory and never include the value of `CLIPROXY_API_KEY`.

## Model and credential authority

- CLIProxyAPI owns upstream accounts, credentials, quota, retries, health, and failover.
- `cliproxy-models` stores only the endpoint, exact admitted IDs, stable profile names, and `env_key = "CLIPROXY_API_KEY"`.
- Plain HTTP is loopback-only.
- Exact aliases must exist in both catalogs; ambiguity requires explicit selection.
- No plugin reads or enumerates proxy account files.

## Modern profile transaction

`cliproxy-models` 1.1.0 manages:

```text
~/.codex/config.toml
~/.codex/cliproxy-grok-4-6.config.toml
~/.codex/cliproxy-gemini-3-7-flash.config.toml
```

Security properties:

- no managed legacy profile selector/table;
- parse and ownership validation before mutation;
- symlink/non-regular-file and concurrent-change refusal;
- unmanaged overlay `model`/`model_provider` collision refusal;
- coordinated timestamped mode-`0600` backups;
- atomic temporary-file replacements with fsync;
- whole-state post-validation;
- exact byte/mode rollback and partial-file cleanup on failure;
- byte/mode idempotence with no backup churn.

## Native council and checkpoints

- `codex-moa` uses only Codex's native subagent/tool runtime.
- It does not launch Hermes or implement a second model loop, scheduler, or gateway.
- One writer is the default; recovery is bounded and evidence-driven.
- The checkpoint MCP receives only `CODEX_HOME`, cannot call models or execute commands, rejects sensitive fields/value patterns, and stores immutable mode-`0600` records beneath a mode-`0700` directory.

## Release authority

Releases package tracked source directly and exclude local base/profile files, proxy keys, checkpoints, backups, caches, bootstrap payloads, Hermes sources, and generated output.

## Local hardening

```bash
chmod 600 "$HOME/.cli-proxy-api/.proxy-api-key"
chmod 600 "$HOME/.codex/config.toml"
chmod 600 "$HOME/.codex/cliproxy-grok-4-6.config.toml"
chmod 600 "$HOME/.codex/cliproxy-gemini-3-7-flash.config.toml"
chmod 700 "${CODEX_HOME:-$HOME/.codex}/codex-moa"
```

Keep shell tracing disabled while exporting the key. Never put expanded secrets in dotfiles, arguments, checkpoints, logs, or reports.
