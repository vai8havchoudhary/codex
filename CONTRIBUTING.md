# Contributing

Contributions are welcome when they preserve the plugin’s authority and security boundaries.

## Before changing code

Read:

1. `AGENTS.md`
2. `agent.md`
3. `SETUP.md`
4. the affected production files and tests

CLIProxyAPI must remain the sole owner of upstream accounts, credentials, load balancing, quotas, health, retries, and failover.

## Development rules

- Use Python 3.11+ and the standard library unless a dependency is clearly justified.
- Keep one stable plugin entry point: `plugins/cliproxy-models/scripts/plugin.py`.
- Keep one Codex provider for CLIProxyAPI.
- Never commit or print API-key values, account metadata, local Codex configuration, or backups.
- Reject ambiguity rather than selecting a nearby model or account-specific route.
- Preserve unrelated TOML content and comments.
- Add regression tests for every new mutation, refusal, or endpoint rule.
- Update `SETUP.md` when user-visible commands or prerequisites change.
- Update `CHANGELOG.md` and the manifest version for release-visible changes.

## Validation

Run all gates before opening a pull request:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m unittest discover -s plugins/cliproxy-models/scripts -p 'test_*.py' -v
python3 -m compileall -q plugins/cliproxy-models/scripts tests
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 -m json.tool plugins/cliproxy-models/.codex-plugin/plugin.json >/dev/null
git diff --check
```

A live CLIProxyAPI or Codex Desktop test is useful but must be reported separately from deterministic tests. Never claim it ran when it did not.

## Pull request checklist

- [ ] Plugin, marketplace, manifest, and skill names remain `cliproxy-models`.
- [ ] No secret or account data was added.
- [ ] Exact Grok 4.6 and Gemini 3.7 Flash admission remains fail closed.
- [ ] One-provider multi-account ownership remains intact.
- [ ] Tests cover the changed behavior.
- [ ] Setup and release docs are synchronized.
- [ ] All validation commands pass.
- [ ] Runtime and release limitations are stated honestly.
