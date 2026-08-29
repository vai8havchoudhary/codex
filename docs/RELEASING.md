# Releasing

This document defines the release transaction for the complete `cliproxy` marketplace.

## Version authority

`release.json` is authoritative for the marketplace bundle:

```json
{
  "name": "cliproxy-plugins",
  "version": "1.1.0",
  "plugins": {
    "cliproxy-models": "1.0.0",
    "hermes-moa": "1.0.0"
  }
}
```

Every mapped version must equal `plugins/<name>/.codex-plugin/plugin.json`, and the mapped names must exactly equal marketplace entries. The release tag is `v<release.json version>`. `CHANGELOG.md` must contain a dated section for that marketplace version.

## Pre-release checklist

1. Confirm exact `main` is intended and its `validate` workflow is green.
2. Confirm no key, account data, Codex/Hermes config, backup, cache, log, or generated archive is tracked.
3. Review `README.md`, `SETUP.md`, `SECURITY.md`, `PRIVACY.md`, and `TERMS.md`.
4. Confirm marketplace, `release.json`, directories, manifests, and skills agree on plugin names.
5. Confirm each manifest version equals its `release.json` mapping.
6. Confirm `CHANGELOG.md` has a dated section for the marketplace version.
7. Run all commands under **Development validation** in `README.md`.
8. Run live Codex/Hermes/CLIProxyAPI smoke tests when available and record unavailable gates honestly.

## Publication path A: annotated tag

From exact current `main`:

```bash
VERSION="$(python3 -c 'import json; print(json.load(open("release.json"))["version"])')"
git fetch origin
git switch main
git pull --ff-only
git tag -a "v${VERSION}" -m "CLIProxyAPI Plugins v${VERSION}"
git push origin "v${VERSION}"
```

## Publication path B: guarded promotion branch

For an authorized connector that cannot create tag refs directly, create `release/v<version>` from exact current `main`:

```bash
VERSION="$(python3 -c 'import json; print(json.load(open("release.json"))["version"])')"
git fetch origin
git branch -f "release/v${VERSION}" origin/main
git push origin "release/v${VERSION}"
```

The workflow requires the promotion branch commit to equal current `main`, reruns all gates, creates or verifies the annotated tag, packages the marketplace, and creates/updates the release. Never add commits directly to a promotion branch.

## Release output

The archive is named `<release.name>-<release.version>.zip` and includes the marketplace manifest, all plugin directories, `release.json`, setup/security/legal docs, and changelog. A SHA-256 sidecar is published with it.

The workflow fails closed on mismatched refs, stale promotion branches, conflicting tags, release/plugin/marketplace version drift, missing changelog sections, test failures, or missing assets.

## Post-release verification

```bash
codex plugin marketplace upgrade cliproxy
codex plugin list --marketplace cliproxy --available --json
```

Verify both plugin names and versions, install them in a clean Codex home, run each status flow, and inspect the release ZIP/checksum for secret or config leakage.

Do not move a published tag. Fix defects on `main`, bump the appropriate plugin version(s) plus the marketplace patch version, update the changelog and `release.json`, then publish a new tag or promotion branch.
