# Releasing

This document is the maintainer checklist for publishing `cliproxy-models`.

The version in the plugin manifest is authoritative. A release is published only from the exact current `main` commit, either by pushing the matching annotated tag or by creating the guarded promotion branch described below.

## Version authority

The authoritative version is:

```text
plugins/cliproxy-models/.codex-plugin/plugin.json
```

The release tag must be exactly:

```text
v<manifest version>
```

For manifest version `1.0.0`, the only accepted tag is `v1.0.0`.

`CHANGELOG.md` must contain a dated section for the same version before publication.

## Pre-release checklist

1. Confirm `main` is at the intended release commit.
2. Confirm the merged `validate` workflow is green on that exact commit.
3. Confirm no local keys, Codex configuration, backups, caches, logs, or generated archives are tracked.
4. Review `SETUP.md`, `SECURITY.md`, `PRIVACY.md`, and `TERMS.md`.
5. Confirm the marketplace and manifest both name the plugin `cliproxy-models`.
6. Confirm the marketplace name remains `cliproxy`.
7. Confirm the manifest version and changelog version match.
8. Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m unittest discover -s plugins/cliproxy-models/scripts -p 'test_*.py' -v
python3 -m compileall -q plugins/cliproxy-models/scripts tests
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 -m json.tool plugins/cliproxy-models/.codex-plugin/plugin.json >/dev/null
git diff --check
```

9. Run a live smoke test when available:
   - install or upgrade the marketplace;
   - run plugin status;
   - set up Grok;
   - switch to Gemini;
   - confirm no secret value appears in output or config;
   - confirm a second setup is byte-idempotent.
10. Record any unavailable live gate honestly.

## Publication path A: push the annotated tag

Read the version without printing any secret-bearing environment:

```bash
VERSION="$(
  python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path("plugins/cliproxy-models/.codex-plugin/plugin.json").read_text())["version"])
PY
)"
```

Create and push the annotated tag from the exact current `main` commit:

```bash
git fetch origin
git switch main
git pull --ff-only
git tag -a "v${VERSION}" -m "CLIProxyAPI Models v${VERSION}"
git push origin "v${VERSION}"
```

The workflow refuses a tag that does not equal `v<manifest version>`.

## Publication path B: guarded release branch

This path is intended for an authorized GitHub connector or maintainer environment that can create branches but cannot write tag refs directly.

Create exactly:

```text
release/v<manifest version>
```

from the current `main` commit. For `1.0.0`:

```bash
git fetch origin
git branch -f release/v1.0.0 origin/main
git push origin release/v1.0.0
```

The `release` workflow then:

1. requires the branch name to equal `release/v<manifest version>`;
2. fetches `origin/main` and requires the promotion branch commit to equal current `main`;
3. reruns deterministic validation;
4. creates the missing annotated `v<manifest version>` tag, or verifies an existing tag points to the same commit;
5. builds and checksums the release archive;
6. creates or idempotently updates the GitHub release.

Do not add commits directly to a promotion branch. If `main` changes before publication, delete and recreate the promotion branch from the new intended release commit.

## Release workflow outputs

For either publication path, `.github/workflows/release.yml`:

1. verifies the release ref, manifest version, and dated changelog section;
2. reruns repository and plugin tests;
3. creates `cliproxy-models-<version>.zip`;
4. creates `cliproxy-models-<version>.zip.sha256`;
5. uploads both as workflow artifacts;
6. creates or updates the GitHub release titled `CLIProxyAPI Models v<version>`.

The archive contains only:

```text
.agents/plugins/marketplace.json
plugins/cliproxy-models/
README.md
SETUP.md
CHANGELOG.md
LICENSE
PRIVACY.md
SECURITY.md
TERMS.md
```

A mismatched tag, mismatched branch, stale promotion branch, conflicting existing tag, missing changelog section, failed test, or missing release asset fails closed before publication completes.

## Post-release verification

After the workflow succeeds:

```bash
codex plugin marketplace upgrade cliproxy
codex plugin list --marketplace cliproxy --json
```

Install or upgrade the plugin in a clean Codex home and run:

```text
@cliproxy-models Check my CLIProxyAPI model setup.
```

Verify the release page contains:

- the expected tag and version;
- the versioned ZIP;
- the `.sha256` checksum;
- generated release notes;
- no key, configuration, backup, cache, or log files.

Verify the checksum:

```bash
sha256sum -c cliproxy-models-<version>.zip.sha256
```

On macOS, use:

```bash
shasum -a 256 -c cliproxy-models-<version>.zip.sha256
```

## Rollback

Do not move an existing release tag.

When a release is bad:

1. mark the GitHub release as affected;
2. fix `main`;
3. bump the patch version;
4. update `CHANGELOG.md`;
5. publish a new tag or matching guarded promotion branch;
6. advise users to upgrade or restore their timestamped Codex configuration backup when relevant.

A promotion branch may be deleted after the release is verified. The immutable tag and GitHub release remain the release authority.
