# Releasing

This document is the maintainer checklist for publishing `cliproxy-models`.

The preparation commit does not create a tag or GitHub release. A release is published only when an authorized maintainer pushes a matching version tag.

## Version authority

The version in:

```text
plugins/cliproxy-models/.codex-plugin/plugin.json
```

is authoritative.

A release tag must be exactly:

```text
v<manifest version>
```

For manifest version `1.0.0`, the only accepted tag is `v1.0.0`.

`CHANGELOG.md` must contain a dated section for the same version before tagging.

## Pre-release checklist

1. Confirm `main` is at the intended release commit.
2. Confirm no local keys, Codex configuration, backups, caches, or generated archives are tracked.
3. Review `SETUP.md`, `SECURITY.md`, `PRIVACY.md`, and `TERMS.md`.
4. Confirm the marketplace and manifest both name the plugin `cliproxy-models`.
5. Confirm the marketplace name remains `cliproxy`.
6. Confirm the manifest version and changelog version match.
7. Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m unittest discover -s plugins/cliproxy-models/scripts -p 'test_*.py' -v
python3 -m compileall -q plugins/cliproxy-models/scripts tests
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 -m json.tool plugins/cliproxy-models/.codex-plugin/plugin.json >/dev/null
git diff --check
```

8. Run a live smoke test when available:
   - install or upgrade the marketplace;
   - run plugin status;
   - set up Grok;
   - switch to Gemini;
   - confirm no secret value appears in output or config;
   - confirm a second setup is byte-idempotent.
9. Record any unavailable live gate honestly.

## Tag and publish

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

Create and push an annotated tag:

```bash
git tag -a "v${VERSION}" -m "CLIProxyAPI Models v${VERSION}"
git push origin "v${VERSION}"
```

The `release` workflow then:

1. verifies the tag equals `v<manifest version>`;
2. reruns deterministic validation;
3. creates a versioned ZIP containing the plugin, marketplace manifest, license, and setup documentation;
4. creates a SHA-256 checksum;
5. uploads both assets;
6. creates or updates the GitHub release.

A mismatched tag fails before packaging.

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
- no key, configuration, backup, or cache files.

## Rollback

Do not move an existing release tag.

When a release is bad:

1. mark the GitHub release as affected;
2. fix `main`;
3. bump the patch version;
4. update `CHANGELOG.md`;
5. publish a new tag;
6. advise users to upgrade or restore their timestamped Codex configuration backup when relevant.
