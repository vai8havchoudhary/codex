# Contributing

Contributions must preserve the authority and secret-custody boundaries in [AGENTS.md](AGENTS.md) and [agent.md](agent.md).

## Development

Use Python 3.11 or newer and only the standard library in plugin runtime code. Keep synthetic test keys obviously fake and confined to `test_*.py` files.

Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
for suite in plugins/*/scripts; do
  python3 -m unittest discover -s "$suite" -p 'test_*.py' -v
done
python3 -m compileall -q plugins tests
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
for manifest in plugins/*/.codex-plugin/plugin.json; do
  python3 -m json.tool "$manifest" >/dev/null
done
git diff --check
```

## Pull requests

A pull request should contain one coherent capability, update affected documentation, add regression coverage, and state which live product gates were or were not run. Never include CLIProxyAPI account data, real keys, application config, logs, backups, caches, or release archives.

For a new plugin, add the directory, manifest, skill, commands, tests, marketplace entry, `release.json` mapping, setup docs, changelog entry, validation workflow coverage, and release packaging coverage together.

## Versioning

Plugin manifests version each plugin. `release.json` versions the marketplace bundle and maps every plugin to its exact manifest version. Follow [docs/RELEASING.md](docs/RELEASING.md) for publication.
