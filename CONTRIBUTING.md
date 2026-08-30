# Contributing

Changes must preserve the authority boundaries in `AGENTS.md` and `agent.md`.

## Development process

1. Branch from exact current `main` and record commit/tree guards.
2. Inspect both plugin manifests, `release.json`, `codex-moa/authority.json`, relevant source, and tests.
3. Keep model admission and the modern Codex profile-file transaction in `cliproxy-models`; keep long-horizon coordination in native Codex skills/agents/MCP state custody.
4. Add deterministic regression tests before changing a security, alias, configuration, checkpoint, or release contract.
5. Update README, setup, agent, security, changelog, and release documentation when user behavior changes.
6. Run the complete validation block in `README.md`.
7. Open a pull request with exact test counts and honest unavailable live gates.
8. Independently reread the exact diff and checks; merge only when green.

## Prohibited changes

- account-specific Codex providers;
- persisted proxy key values or account metadata;
- silent selection between ambiguous Gemini aliases;
- managed top-level `profile` selectors or `[profiles.*]` tables;
- partial or non-transactional base/profile updates;
- overwriting unmanaged profile-file `model` or `model_provider` keys;
- Hermes dependencies or another model loop/scheduler/gateway;
- checkpoint tools that execute commands or call models;
- bootstrap/base64 source delivery or materialization workflows;
- release tags from unvalidated or non-main commits.

## Required configuration tests

Cover:

- fresh base plus two overlay creation;
- migration of only the plugin's managed legacy block;
- preservation of unrelated TOML/comments;
- unmanaged collisions and malformed TOML/markers;
- regular-file/symlink and mode checks;
- coordinated backups, post-validation, idempotence, and exact rollback after injected partial failure;
- profile-file shape compatible with `codex --profile`;
- `codex-moa` base-provider plus overlay validation.

Also retain exact alias, versioned cache, checkpoint MCP, plugin layout, release guard, and obsolete-path tests.
