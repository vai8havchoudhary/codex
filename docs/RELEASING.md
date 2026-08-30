# Releasing the CLIProxyAPI native Codex marketplace

`release.json` is authoritative for the marketplace bundle version and every plugin manifest version.

## Current release contract

```json
{
  "name": "cliproxy-plugins",
  "version": "2.0.0",
  "plugins": {
    "cliproxy-models": "1.0.0",
    "codex-moa": "2.0.0"
  }
}
```

The release tag must be exactly `v<release.version>`. `CHANGELOG.md` must contain a dated section for that version.

## Pre-release checklist

1. Confirm the exact intended `main` commit and tree.
2. Confirm merged-main validation is green on that SHA.
3. Confirm `.bootstrap/`, `materialize-native-moa.yml`, and `plugins/hermes-moa` are absent.
4. Confirm marketplace entries equal the keys in `release.json`.
5. Confirm every mapped version equals its plugin manifest.
6. Confirm both plugin docs reflect current live alias behavior.
7. Run the full validation block in `README.md`.
8. Run an exact-main live installation and CLIProxyAPI/Codex smoke gate when available.
9. Record unavailable live gates honestly.

Do not publish before the exact-main live gate when release adjudication requires it.

## Publication path A: annotated tag

From exact current `main`:

```bash
git fetch origin
git switch main
git pull --ff-only
git tag -a v2.0.0 -m "CLIProxyAPI Plugins v2.0.0"
git push origin v2.0.0
```

The workflow refuses a tag that does not match `release.json` or does not pass validation.

## Publication path B: guarded promotion branch

For an authorized connector that cannot directly create tag refs, create exactly:

```text
release/v2.0.0
```

at exact current `main`. The workflow requires the branch SHA to equal `origin/main`, reruns all gates, creates or verifies the annotated tag, builds the archive, and publishes the release.

Do not add commits to a promotion branch. If `main` changes, delete/recreate the branch from the newly adjudicated commit.

## Release archive

The workflow packages tracked source directly:

```text
.agents/plugins/marketplace.json
plugins/
release.json
README.md
SETUP.md
CHANGELOG.md
LICENSE
PRIVACY.md
SECURITY.md
TERMS.md
```

It must include `cliproxy-models` and `codex-moa`. Bootstrap archives, Hermes sources, materialization workflows, local configuration, keys, checkpoints, backups, caches, and build output must remain absent.

## Post-release verification

Verify tag target, release assets, checksum, archive contents, marketplace installation, exact model preflight, native checkpoint MCP discovery, and one bounded council smoke task.

Do not move a published tag. Fix forward with a new patch version.
