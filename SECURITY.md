# Security policy

## Supported versions

Security fixes are applied to the latest `2.x` marketplace release. Upgrade to the newest published bundle before reporting a problem.

## Reporting a vulnerability

Do not open a public issue containing API keys, account identifiers, local configuration, checkpoint contents, backup contents, or exploit details.

Prefer a private GitHub security advisory. A useful report includes the affected plugin/version/commit, Codex version, operating system, redacted reproduction steps, expected and observed authority boundary, and whether any value was printed, persisted, or transmitted unexpectedly.

Never include the value of `CLIPROXY_API_KEY`.

## Security model

### Model authority

- CLIProxyAPI owns every upstream account, credential, quota, retry, health, and failover decision.
- `cliproxy-models` stores only the proxy endpoint, exact admitted model IDs, stable profile names, and `env_key = "CLIPROXY_API_KEY"`.
- Plain HTTP is limited to loopback endpoints.
- Exact aliases must appear in both CLIProxyAPI catalogs.
- Ambiguous Gemini aliases require explicit selection; discovery never chooses account policy.
- Configuration writes are preflighted, atomic, backed up, mode `0600`, post-validated, and idempotent.

### Native council authority

- `codex-moa` uses Codex's own subagent and tool runtime.
- It does not launch Hermes Agent or implement a second model loop, scheduler, or gateway.
- The default is one writer; advisors and reviewers are read-only.
- Recovery is bounded and driven by concrete validation evidence.

### Checkpoint authority

- The MCP process receives only `CODEX_HOME`.
- It cannot call models, route accounts, or execute repository commands.
- Checkpoints reject sensitive field names and common secret-value patterns.
- Storage uses a mode-`0700` directory, mode-`0600` immutable records, opaque handles, SHA-256 digests, atomic writes, symlink refusal, and run continuity checks.

### Release authority

- Releases package tracked source directly.
- Bootstrap payloads and materialization workflows are prohibited.
- Archives exclude local configuration, proxy keys, checkpoints, backups, caches, and generated output.

## Local hardening

```bash
chmod 600 "$HOME/.cli-proxy-api/.proxy-api-key"
chmod 600 "$HOME/.codex/config.toml"
chmod 700 "${CODEX_HOME:-$HOME/.codex}/codex-moa"
```

Keep shell tracing disabled while exporting the key. Do not place the expanded secret value in dotfiles, command-line arguments, checkpoints, logs, or issue reports.
