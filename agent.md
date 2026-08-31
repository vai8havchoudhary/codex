# Architecture and maintainer handbook

## Product boundary

### `cliproxy-models` 1.1.0

The sole model-admission and Codex-provider configuration authority. It reads both CLIProxyAPI catalogs, admits exact common IDs, refuses ambiguity, and writes one provider plus three model overlays and two named council overlays. It persists only the environment-variable name `CLIPROXY_API_KEY`; it never inspects proxy accounts, persists key values, or chooses routing policy.

Managed documents:

```text
~/.codex/config.toml
~/.codex/cliproxy-grok-4-6.config.toml
~/.codex/cliproxy-gemini-3-7-flash.config.toml
~/.codex/cliproxy-luna.config.toml
~/.codex/luna-grok.config.toml
~/.codex/grok-gemini.config.toml
~/.codex/cliproxy-council-models.json
```

The base owns the shared provider and selected default. Each overlay owns managed top-level `model` and `model_provider` keys. Named council overlays also own root-only `developer_instructions`, with collision refusal. Legacy `[profiles.*]` tables and top-level profile selectors are not current Codex configuration.

The seven paths form one transaction: snapshot, ownership/path validation, coordinated backups, atomic replacements, post-validation, and exact rollback. Existing files become mode `0600`; new files are created mode `0600`. Equal bytes and safe modes are a no-op. User-owned collisions and malformed or unsafe paths are refused rather than overwritten.

### `codex-moa` 2.0.0

A native Codex coordination policy using Codex's own agent tree, model overrides, messaging, bounded forks, skills, commands, and checkpoint MCP server. It contains no external model loop.

The supported councils are `luna-grok` (exact `gpt-5.6-luna` root and `grok-4.6` reviewer) and `grok-gemini` (`grok-4.6` root and `gemini-3.7-flash-high` reviewer). Gemini-led is unsupported. The root is the coordinator and default single writer. The opposite model is consulted at plan criticism, concrete-failure recovery and independent final review—not after every step. Luna's Grok advisor also localizes; the Grok root localizes itself before supplying Gemini evidence.

## Packaged authority dependency

```text
marketplace:       cliproxy
release:           cliproxy-plugins 2.0.0
consumer:          codex-moa 2.0.0
model authority:   cliproxy-models 1.1.0
required scripts:  catalog.py, plugin.py
```

Source and installed-cache discovery are release/pin bound. No highest/newest/first-version selection is allowed. Preflight loads model admission from the exact authority, then validates the provider in base `config.toml` and all model overlays plus the selected council overlay.

## Live alias contract

VPS2 evidence on 2026-08-30 shows `grok-4.6`, `gemini-3.7-flash-high`, and `gemini-3.7-flash-advisor`, with no bare Gemini alias. Automatic Gemini resolution must fail. Explicit `--gemini-model gemini-3.7-flash-high` is accepted only when present in both catalogs and equal to the profile overlay.

## Native council lifecycle

```text
preflight -> localize -> plan -> implement -> validate -> review -> complete
                                      |           |
                                      +-> recover-+
```

- localize before editing;
- accept one dependency-aware plan;
- keep one writer unless disjoint ownership is explicit;
- treat repository gates as authoritative;
- allow at most two coherent repair rounds per blocker;
- record immutable checkpoints and reconcile live state on resume;
- for Luna, reserve a proven read-only Grok final reviewer before implementation and reuse the localizer as plan critic;
- for Grok, gather source at the root; Gemini reviewed supplied evidence only through fresh single-turn plan criticism and distinct fresh final review, with no tools, READY reservation, follow-ups or history reuse;
- bound each Gemini semantic gate to one primary plus at most one fresh transport retry; capability exhaustion blocks, never resets as implementation repair; complete initial packets and packet SHA-256/native references are required by policy;
- require an actual returned opposite-model final verdict on the final diff and evidence;
- schema-2 records enforce exact council identity and structured reviewer witnesses; schema-1 records are read-only historical evidence, and payload checksums do not authenticate claimed native calls.
- preserve historical schema-2 read/digest compatibility; enforce Gemini final-reviewer freshness only on new writes across the entire same-run history, not merely the current payload.

## Checkpoint MCP boundary

The MCP is a state store, not an orchestrator. It receives only `CODEX_HOME`, stores compact immutable mode-`0600` records beneath a mode-`0700` directory, rejects secret fields/values and symlinks, and cannot call models or execute repository commands.

## Release authority

`release.json`, plugin manifests, and `authority.json` must align before validation succeeds. Bundle 2.0.0 intentionally includes a new `cliproxy-models` 1.1.0 because the historically released 1.0.0 bytes used obsolete profile tables and are immutable.

The pre-correction exact-main provider/MCP/council evidence is documented in `docs/VPS2_GATE_2026-08-30.md`. The untagged 2.0.0 release candidate retains its version during this correctness correction; do not bump merely to invalidate caches. A fresh exact-main reinstall and long-horizon run of each named council is still mandatory before creating `v2.0.0`.

Fail closed when exact aliases, authority versions, profile documents, repository authority, writer ownership, checkpoint safety, or validation evidence are unresolved.

## Stable native council catalog

Named council overlays own `model_catalog_json`, pointing at the transaction-managed `cliproxy-council-models.json` beside the base config. It contains the exact three admitted models with the original live Codex-catalog metadata; capabilities are never synthesized. The JSON ownership marker is `_codex_cliproxy_models: 1`. Unmanaged or malformed JSON, duplicates/missing models, unsafe paths, and concurrent changes fail closed. The seventh file shares backups, mode 0600, post-validation, idempotence and exact rollback with all six TOML documents.

This derived startup snapshot keeps native subagent model selection independent of mutable shared catalog-cache entries. It is not a second alias authority: preflight still reads both live proxy catalogs and refuses stale snapshot metadata. The base default is not pinned to this three-model snapshot, so an unrelated admitted default is preserved by `--default preserve`. Restart Codex after setup/catalog refresh.
