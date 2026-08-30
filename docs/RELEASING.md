# Releasing the CLIProxyAPI native Codex marketplace

`release.json` is authoritative for the bundle version and every plugin manifest version.

## Current release contract

```json
{
  "name": "cliproxy-plugins",
  "version": "2.0.0",
  "plugins": {
    "cliproxy-models": "1.1.0",
    "codex-moa": "2.0.0"
  }
}
```

`codex-moa/authority.json` must pin the same bundle, consumer, and `cliproxy-models` 1.1.0 authority.

The model-plugin minor bump is mandatory: `cliproxy-models` 1.0.0 has historical released bytes that generated obsolete `[profiles.*]` tables. Do not silently replace or reinterpret those immutable bytes.

## Pre-release checklist

1. Confirm exact intended `main` commit and tree and green merged-main validation.
2. Confirm marketplace, `release.json`, manifests, and `authority.json` align.
3. Confirm `.bootstrap/`, materialization workflow, and `plugins/hermes-moa` are absent.
4. Run the complete validation block in README.md.
5. On exact main, fresh-install both versions from the live marketplace.
6. Run automatic Gemini ambiguity refusal and explicit `gemini-3.7-flash-high` setup.
7. Verify base `config.toml` contains no `profile` selector or `[profiles.*]` table.
8. Verify both separate profile files exist, are mode `0600`, and work with `codex exec --profile`.
9. Verify setup idempotence, default switching/restoration, exact model preflight, checkpoint MCP round trip, and one bounded native council.
10. Record exact evidence and unresolved blockers honestly.

The prior evidence in `VPS2_GATE_2026-08-30.md` is useful but predates the profile-file correction. Do not publish before the fresh exact-main gate.

## Publication paths

Only after owner adjudication:

- annotated tag exactly `v2.0.0`; or
- guarded branch exactly `release/v2.0.0` at exact current `main`.

The workflow requires the promotion branch to equal `origin/main`, reruns all gates, creates/verifies the annotated tag, and packages tracked source. Do not move a published tag. Do not add commits to a promotion branch.

## Release archive

The archive must contain both native plugins, `release.json`, marketplace metadata, and public setup/security documentation. It must not contain local Codex config/profile files, API keys, checkpoints, backups, caches, bootstrap payloads, Hermes sources, or materialization workflows.

## Post-release verification

Verify tag target, release assets/checksum, archive contents, installed versions 1.1.0/2.0.0, modern profile execution, exact preflight, MCP discovery/round trip, and a bounded council smoke run.
