# Architecture and maintainer handbook

## Product boundary

The marketplace exposes one model-setup plugin and one native long-horizon coordination plugin.

### `cliproxy-models`

This is the sole model-admission and Codex-provider configuration authority. It:

- reads both CLIProxyAPI model catalog views;
- admits exact Grok 4.6 and Gemini 3.7 Flash aliases only when the same ID appears in both;
- refuses ambiguity and nearby versions;
- writes one provider and two stable Codex profiles;
- persists only `env_key = "CLIPROXY_API_KEY"`;
- preserves unrelated TOML and writes atomically.

It does not inspect proxy account files or choose account-routing policy.

### `codex-moa`

This plugin is a native Codex coordination policy. It uses Codex's own agent tree, model overrides, messaging, bounded history forks, skills, commands, and agent definitions. It contains no external model loop.

The root thread is the coordinator and default single writer. Other models are consulted at high-leverage boundaries:

1. localization;
2. plan criticism;
3. recovery after concrete validation failure;
4. independent final review.

The policy intentionally avoids permanent multi-model debate. One accepted plan and one acting patch trajectory preserve coherence.

## Live alias contract

VPS2 evidence on 2026-08-30 shows:

```text
grok-4.6
gemini-3.7-flash-high
gemini-3.7-flash-advisor
```

No bare `gemini-3.7-flash` exists. Both qualified Gemini aliases match the requested family/version/marker, so automatic resolution must raise an ambiguity error. Explicit `--gemini-model gemini-3.7-flash-high` is valid only if that exact ID is in both catalog views and the configured Codex profile matches it.

Do not encode a preference between `-high` and `-advisor` in discovery logic.

## Native council lifecycle

```text
preflight -> localize -> plan -> implement -> validate -> review -> complete
                                      |           |
                                      +-> recover-+
```

- **Preflight:** verify repository/task authority and exact model admission.
- **Localize:** bounded read-only explorers answer distinct repository questions.
- **Plan:** one writer synthesizes a dependency-aware plan; the opposite model challenges it.
- **Implement:** one writer owns the patch surface unless explicit disjoint ownership is necessary.
- **Validate:** repository-native commands and tests are authoritative.
- **Recover:** open only after concrete failure or invalidated evidence; at most two coherent repair rounds.
- **Review:** an opposite-model read-only verifier reviews the actual diff and gate evidence.
- **Complete/blocked:** record the exact terminal state in an immutable checkpoint.

## Checkpoint MCP boundary

`plugins/codex-moa/mcp/server.py` is a state store, not an orchestrator.

Allowed tools:

- `checkpoint_validate`
- `checkpoint_put`
- `checkpoint_get`
- `checkpoint_list`

Records contain objectives, decisions, evidence, changed paths, validation state, risks, retry budget, and next action. They exclude source-file bodies, conversations, credentials, tokens, cookies, account data, and environment dumps.

Storage properties:

- under `${CODEX_HOME:-~/.codex}/codex-moa/checkpoints`;
- directory mode `0700`;
- record mode `0600`;
- immutable opaque handles;
- canonical SHA-256 digest;
- atomic replace and directory sync;
- equal writes return the existing handle;
- symlink paths are refused;
- previous links must exist and retain `run_id` continuity.

The MCP process receives only `CODEX_HOME`. Never add `CLIPROXY_API_KEY` or account-directory variables to `.mcp.json`.

## Research-to-policy mapping

The detailed references live in `plugins/codex-moa/references/long-horizon-research.md`.

- SWE-agent and Agentless support deliberate repository interfaces, localization, and direct validation feedback.
- CodePlan and MASAI support dependency-aware plans and bounded specialist roles.
- Mixture-of-Agents supports model-diverse independent proposals, adapted here to high-leverage gates rather than every step.
- Reflexion supports evidence-driven repair with compact external memory.

These sources inform policy; none is copied as a competing runtime.

## Release authority

`release.json` must map every marketplace plugin to the exact manifest version. The release workflow accepts only:

- annotated `v<release.version>` tags; or
- exact-current-main `release/v<release.version>` promotion branches.

It reruns all tests and packages the tracked source tree directly. Bootstrap archives, materialization workflows, generated source commits, and mutable release tags are forbidden.

## Failure policy

Fail closed when exact aliases are unresolved, repository authority changed, writer ownership overlaps, required destructive work is unauthorized, a checkpoint path is unsafe, or the repair budget is exhausted. Record the exact blocker; never convert missing evidence into a success claim.
