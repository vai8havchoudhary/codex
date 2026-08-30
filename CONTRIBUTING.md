# Contributing

Changes must preserve the authority boundaries in `AGENTS.md` and `agent.md`.

## Development process

1. Branch from current `main`.
2. Inspect both plugin manifests, `release.json`, relevant source, and tests.
3. Keep model admission in `cliproxy-models`; keep long-horizon coordination in native Codex skills/agents/MCP state custody.
4. Add deterministic regression tests before changing a security, alias, checkpoint, or release contract.
5. Update README, setup, agent, security, and changelog documentation when user behavior changes.
6. Run the complete validation block in `README.md`.
7. Open a pull request with exact test counts and honest unavailable live gates.
8. Merge only after the exact PR head and merged-main checks are green.

## Prohibited changes

- account-specific Codex providers;
- persisted proxy key values or account metadata;
- silent selection between ambiguous Gemini aliases;
- Hermes Agent dependencies;
- a custom model loop or scheduler inside `codex-moa`;
- checkpoint tools that execute commands or call models;
- bootstrap/base64 source delivery or materialization workflows;
- release tags from unvalidated or non-main commits.

## Tests

At minimum, cover:

- both CLIProxyAPI catalog shapes;
- exact alias intersection and ambiguity;
- explicit alias presence in both catalogs;
- provider/profile consistency;
- plugin/marketplace/release layout;
- MCP protocol and storage permissions;
- checkpoint validation, idempotence, chaining, secret refusal, and symlink refusal;
- absence of Hermes/bootstrap/materialization paths;
- release workflow guards and public archive contents.

## Live model regression contract

Keep regression coverage for `grok-4.6`, `gemini-3.7-flash-high`, and `gemini-3.7-flash-advisor`. Automatic Gemini resolution must refuse the two-candidate catalog; explicit exact selection must still require the same ID in both catalogs. Never log or persist `CLIPROXY_API_KEY`.
