---
name: codex-moa
description: Coordinate native Codex subagents across Grok 4.6 and Gemini 3.7 Flash for long-horizon repository coding. Use for multi-file, high-uncertainty, or validation-heavy work that benefits from model-diverse localization, planning, recovery, and independent review. Do not use for a narrow edit that one agent can complete directly.
---

# Native Codex MoA for long-horizon coding

This plugin is a coordination policy for Codex's own multi-agent tools. It is not an alternate agent runtime. Never invoke Hermes Agent, create a second orchestration loop, or move CLIProxyAPI account routing into this plugin.

## Authority boundary

- Codex owns threads, subagents, tools, permissions, sandboxing, repository writes, and user interaction.
- `cliproxy-models` owns exact model admission and the two Codex profiles.
- CLIProxyAPI owns upstream accounts, OAuth sessions, credentials, quotas, health checks, retries, and failover.
- `codex-moa-checkpoints` stores only compact immutable milestone records. It never calls a model or executes code.

Never read, enumerate, print, summarize, or persist proxy account files or the value of `CLIPROXY_API_KEY`.

## Activation gate

Use a council when at least one condition is true:

- the task spans multiple dependent files or subsystems;
- the installed/runtime path is uncertain;
- the task has destructive migration or security implications;
- the validation surface is broad or failures are likely to be ambiguous;
- the work is expected to require several milestones or may need resumption;
- a model-diverse review can materially alter the plan.

For a single obvious edit, use normal Codex execution. Extra agents are not a quality substitute for repository evidence.

## Preflight

1. Read the repository's `AGENTS.md` and nearest instructions.
2. Inspect the working tree, current branch, task authority, and validation commands.
3. Resolve this plugin's root and run:

```bash
python3 <codex-moa-root>/scripts/preflight.py --json
```

The preflight delegates model resolution to the sibling `cliproxy-models` authority and then verifies the installed Codex profiles. It must succeed before spawning model-specific agents.

The observed VPS2 catalog may export both `gemini-3.7-flash-high` and `gemini-3.7-flash-advisor` without a bare `gemini-3.7-flash`. Automatic selection must fail as ambiguous. Select one exact alias explicitly through `cliproxy-models`, for example:

```text
@cliproxy-models Set up with --gemini-model gemini-3.7-flash-high.
```

Then rerun preflight with the same exact selection when needed:

```bash
python3 <codex-moa-root>/scripts/preflight.py \
  --gemini-model gemini-3.7-flash-high \
  --json
```

Do not choose between `-high` and `-advisor` silently.

4. Establish `run_id`, leader mode, exact leader model, exact advisor model, constraints, owned paths, and a retry budget of at most two.
5. Write a `preflight` checkpoint through `checkpoint_put`.

## Leader modes

- `grok-led`: Grok 4.6 is the acting writer; Gemini 3.7 Flash is the independent advisor/reviewer.
- `gemini-led`: Gemini 3.7 Flash is the acting writer; Grok 4.6 is the independent advisor/reviewer.

The root Codex thread is the coordinator and, by default, the only writer. Model-diverse subagents are read-only unless the root assigns a disjoint file boundary explicitly.

Use Codex native tools directly: `spawn_agent`, `send_message`, `followup_task`, `wait_agent`, `list_agents`, `interrupt_agent`, and `close_agent`. Do not wrap them in a custom scheduler.

## Long-horizon state machine

Use these phases in order unless evidence requires a bounded return to an earlier phase:

```text
preflight -> localize -> plan -> implement -> validate -> review -> complete
                                      |           |
                                      +-> recover-+
```

Checkpoint after each phase and after every material plan change.

### 1. Localize

Use one or two read-only explorer agents with independent questions. Prefer different models when two genuinely distinct views are useful.

Good localization tasks:

- identify the installed production path and its callers;
- map the relevant schema, tests, and release contracts;
- locate conflicting authorities or compatibility layers;
- identify the smallest coherent ownership boundary.

Require evidence with paths, symbols, and observed behavior. Do not ask explorers to propose broad rewrites. Avoid duplicating the same question across agents.

Use bounded context forks. For a fresh repository question, prefer `fork_turns="none"` and include the exact task, constraints, and checkpoint handle. For a tightly related follow-up, reuse the existing agent with `followup_task` or `send_message` instead of spawning another.

### 2. Plan

The acting writer synthesizes one implementation plan. Send that plan to the opposite-model critic for an independent challenge covering:

- missing dependencies and callers;
- authority and security boundaries;
- unsafe migration ordering;
- insufficient validation;
- rollback, cleanup, or compatibility risks;
- unnecessary scope.

Accept one plan. Record rejected alternatives and why they were rejected. Do not maintain parallel competing patch trajectories.

### 3. Implement

Use single-writer ownership:

- only the acting writer edits the task surface by default;
- advisors, localizers, and reviewers remain read-only;
- a spawned worker may write only when given an explicit disjoint path list and responsibility;
- tell every writing agent that other work may exist and it must not revert unrelated changes;
- never assign overlapping files to concurrent writers.

Implement one coherent milestone at a time. After each milestone, record changed paths, decisions, evidence, risks, and the next validation command.

### 4. Validate

Run repository-native gates, not model confidence checks. Record exact commands, exit codes, and concise failure evidence.

A milestone advances only when its required gates pass. A passing narrow test does not replace a required broader gate. Do not describe queued CI as passed.

### 5. Recover

Open a recovery council only when evidence warrants it:

- a required validation command fails unexpectedly;
- new repository evidence invalidates the accepted plan;
- the same failure survives one repair attempt;
- a public contract or authority boundary remains materially uncertain.

Send the opposite-model recovery agent the checkpoint handle, exact failure command, exit code, minimal relevant output, current diff summary, and remaining retry budget. Ask for ranked causal hypotheses and the smallest discriminating checks.

Maximum repair budget: two coherent repair rounds per blocker. On exhaustion, write a `blocked` checkpoint and stop rather than looping.

### 6. Review

Before completion, spawn an opposite-model read-only reviewer that did not own the final patch. Require review of the actual diff and gate evidence for:

- complete requirement coverage;
- unintended scope or stale files;
- safety and authority regressions;
- missing negative tests;
- invalid release/version claims;
- cleanup and rollback behavior.

Address material findings within the remaining repair budget, rerun affected gates, then write the final checkpoint.

## Checkpoint contract

A checkpoint contains only compact execution state:

- objective and phase;
- exact leader/advisor model IDs;
- constraints and accepted decisions;
- evidence with commands and exit codes;
- owned and changed paths;
- validation state;
- risks, retry budget, and next action;
- optional previous checkpoint handle.

Do not put source files, full conversations, credentials, tokens, cookies, account identifiers, or raw environment dumps into checkpoints. Use the opaque handle to resume; inspect the repository again instead of trusting stale narrative context.

## Resume

1. Call `checkpoint_get` with the supplied handle.
2. Verify the current repository, branch, head, worktree, and task authority against the checkpoint.
3. Rerun model preflight.
4. Revalidate the last passed milestone if the repository changed.
5. Continue from `next_action`, or create a `blocked` checkpoint if the state cannot be reconciled safely.

## Stop conditions

Stop fail-closed when:

- exact models cannot be admitted in both CLIProxyAPI catalogs;
- model alias ambiguity remains unresolved;
- repository authority differs from the task guard;
- the writer cannot establish exclusive or disjoint ownership;
- a required destructive action lacks authorization;
- the repair budget is exhausted;
- required validation cannot be run and no honest alternative evidence exists.

A stopped run must leave a compact `blocked` checkpoint with the exact remaining blocker. Never claim completion from a plan, an agent opinion, or a queued workflow.
