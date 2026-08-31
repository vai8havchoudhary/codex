---
name: codex-moa
description: Coordinate long-horizon repository tasks with native Codex subagents using luna-grok (Luna writes, Grok reviews) or grok-gemini (Grok writes, Gemini reviews). Use for model-diverse multi-file implementation, validation-heavy work, or checkpoint resumption; not ordinary narrow edits.
---

# Native Codex MoA

This is a policy for Codex's native agent tools, not another scheduler or model loop. CLIProxyAPI owns model routing and credentials; `cliproxy-models` admits exact IDs and owns the shared provider/profile transaction. The checkpoint MCP stores state only; it cannot call models or execute commands. Never read, enumerate, print, summarize, or persist proxy account files or the value of `CLIPROXY_API_KEY`.

## Choose the named council

| Council / profile | Acting root and single writer | Read-only advisor/reviewer |
| --- | --- | --- |
| `luna-grok` | `gpt-5.6-luna` | `grok-4.6` |
| `grok-gemini` | `grok-4.6` | `gemini-3.7-flash-high` |

Start with `codex --profile luna-grok` or `codex --profile grok-gemini`. The matching discoverable skill also selects that council. A skill cannot change the root model: if the actual session model differs, stop and ask to restart with the named profile. Do not choose `gpt-5.6-luna-advisor`, an alias, or another model as a substitute.

Gemini-led is unsupported: the qualified Gemini root did not expose native spawn tools. Historical `gemini-led` checkpoints are readable evidence only, not proof that a new council can run. The old `grok-led` command aliases `grok-gemini`.

## Preflight and native capability witness

1. Read repository instructions; inspect the branch, worktree, task scope, writer ownership, and repository-native validation commands.
2. Run the installed plugin's preflight with the selected council and the *observed* root model:

```bash
python3 <codex-moa-root>/scripts/preflight.py --council luna-grok \
  --leader-model gpt-5.6-luna --gemini-model gemini-3.7-flash-high --json
```

For `grok-gemini`, pass `--leader-model grok-4.6`. Preflight checks both proxy catalogs, exact pinned model authority, base provider, model overlays, and the selected council overlay. It does not prove native delegation works. Gemini `gemini-3.7-flash-high` and `gemini-3.7-flash-advisor` can both be published; automatic selection must fail. Do not choose between them silently. Set up explicitly through `cliproxy-models`; this council contract uses High.

3. Confirm the checkpoint MCP and native `spawn_agent`, messaging and wait tools are actually callable. Before editing, spawn one read-only opposite-model localizer, require a real returned response, and retain its actual agent ID. Reserve a second opposite-model read-only reviewer now with a short readiness-only request, wait for its response, and retain it. This prevents discovering a changed runtime model catalog only at the final gate.
4. If either spawn/model override is rejected, or no actual opposite-model response returns, write `blocked` if possible and stop. Never simulate an agent, invent its ID, or use direct proxy calls as proof of native delegation.
5. Establish a schema-2 `run_id`, `council`, equal `leader_mode`, exact leader/advisor IDs, constraints, owned paths, and retry budget at most two; write `preflight` through `checkpoint_put`.

## Bounded single-writer lifecycle

```text
preflight -> localize -> plan -> implement -> validate -> review -> complete
                                      |           |
                                      +-> recover-+
```

- **Localize:** use the one proven advisor for paths, callers, tests, and authority boundaries. Supply what the root already knows so it does not repeat discovery. Require concise evidence, not full files or repeated diffs.
- **Plan:** the root synthesizes one dependency-aware plan and sends it to the same localizer as critic. Reuse its context; do not launch a second investigation. Accept one acting trajectory.
- **Implement:** root is the single-writer. Both advisors stay read-only. User authorization still limits edits and external mutations. Do not give overlapping files to concurrent writers.
- **Validate:** run repository-native gates at coherent milestones, record exact commands/exit codes, and distinguish narrow checks from required full gates. Queued CI is not a pass.
- **Recover:** only for concrete failed gates or invalidated assumptions. Reuse the critic with the minimal failure evidence. Allow two coherent repair rounds per blocker; checkpoint `blocked` when exhausted.
- **Review:** send the reserved independent reviewer the final diff/revision, requirements, and validation evidence. It has never written the patch. Require an actual returned `APPROVE` or `REQUEST_CHANGES` plus concrete evidence. A readiness acknowledgement is not review. If that agent is unavailable, one fresh reviewer attempt is allowed; if runtime rejects it, a retained read-only critic may review the final patch with the reduced independence disclosed. Never use the writer's own approval.
- **Complete:** only after material findings are resolved, required gates pass, and an opposite-model final verdict covers the final patch. Close the retained agents after storing the final record.

Keep at most two live read-only advisors. Use bounded native waits (tool default, or integer timeout arguments) while the root does independent useful work. Do not poll rapidly or manufacture elapsed time with sleep. Budget at most five minutes per advisory gate with one focused follow-up; on no response, record the blocker instead of endless respawns. Do not rerender the whole diff after every tool call; give agents a path/revision and concise delta evidence.

Checkpoint at semantic milestones, not after every shell command. Keep logs, source files, and conversation transcripts outside checkpoint payloads.

## Checkpoints and evidence

New writes use schema 2. `council` and `leader_mode` must both be `luna-grok` or `grok-gemini`; exact leader and the single advisor model must match the table. Run identity cannot change inside a chain or by omitting `previous`.

Record observed native responses in `native_agents` (maximum four role witnesses):

```json
{
  "role": "reviewer",
  "model": "grok-4.6",
  "agent_id": "<actual native runtime agent ID>",
  "verdict": "APPROVE",
  "summary": "<concise returned final review evidence>",
  "transcript_ref": "<log path and event/line reference>",
  "reviewed_revision": "<commit SHA or final diff SHA-256>"
}
```

Roles are `localizer`, `critic`, `reviewer`, or `recovery`; non-review responses may use `OBSERVED`. Preserve the actual response reference and never transform a failed review into approval. Every reviewer requires a final revision.

A `complete` record must follow a `review` record with unchanged witnesses, changed paths, and passing validation evidence (exit code 0). It requires a returned reviewer `APPROVE`. Store/checksum validation proves payload shape and integrity, **not** that the model's claim is truthful. The caller must independently match witness IDs, exact models, returned verdicts and final revision against actual native runtime events. A self-written “Grok approved” sentence is not proof.

## Resume and stop

Read `checkpoint_get`, reconcile current repository/branch/HEAD/worktree with the record, rerun preflight, and reestablish actual native agents; old agent IDs may no longer be live. Revalidate stale milestones. Schema-1 records remain readable with their original digest but are not accepted for new writes: start a new schema-2 run, reference the historical handle in evidence, and perform the missing capability/review gates.

Stop fail-closed on missing model admission, unsupported direction, unavailable native tools, identity mismatch, uncertain write ownership, unapproved destructive scope, exhausted recovery, or missing required validation/review. Never claim completion from elapsed time, process exit alone, a plan, self-attested review, or a queued workflow.
