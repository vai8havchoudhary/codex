# Security policy

## Supported versions

Security fixes are applied to the latest `1.x` release line. Users should upgrade to the newest published plugin version before reporting a problem.

## Reporting a vulnerability

Do not open a public issue containing API keys, account identifiers, local configuration, backup contents, or exploit details.

Prefer a private GitHub security advisory for this repository. When that channel is unavailable, contact the repository owner privately through GitHub and provide only the minimum information needed to establish a secure reporting channel.

A useful report includes:

- affected plugin version and commit;
- Codex version and operating system;
- whether CLIProxyAPI was loopback or HTTPS remote;
- redacted reproduction steps;
- expected and observed security boundary;
- whether any secret value was printed, persisted, or transmitted unexpectedly.

Never include the value of `CLIPROXY_API_KEY`.

## Security model

The plugin is intentionally narrow:

- CLIProxyAPI owns all upstream accounts and credentials.
- Codex stores only the proxy endpoint, stable aliases, and `env_key = "CLIPROXY_API_KEY"`.
- Plain HTTP is limited to loopback endpoints.
- Aliases must appear exactly in both provider catalogs.
- Configuration changes are preflighted, atomic, backed up, mode `0600`, and post-validated.
- Failed admission performs no write.
- Release archives exclude local configuration, caches, keys, and backups.

## Local hardening

Protect the key file and Codex configuration:

```bash
chmod 600 "$HOME/.cli-proxy-api/.proxy-api-key"
chmod 600 "$HOME/.codex/config.toml"
```

Keep shell tracing disabled while exporting the key, and do not place the expanded secret value in dotfiles or command-line arguments.
