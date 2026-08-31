# CLIProxyAPI native plugins for Codex

[![validate](https://github.com/vai8havchoudhary/codex/actions/workflows/validate.yml/badge.svg)](https://github.com/vai8havchoudhary/codex/actions/workflows/validate.yml)

A native Codex plugin marketplace for safely admitting multiple CLIProxyAPI-backed models and coordinating long-horizon coding through Codex's own subagent runtime.

| Plugin | Version in bundle 2.0.0 | Purpose |
|---|---:|---|
| `cliproxy-models` | 1.1.0 | Admit exact Luna, Grok 4.6 and Gemini 3.7 Flash IDs, configure one CLIProxyAPI provider, and maintain modern Codex profile overlay files. |
| `codex-moa` | 2.0.0 | Run bounded model-diverse councils with native Codex agents and immutable checkpoint MCP state. |

Neither plugin requires Hermes or introduces another orchestration runtime. CLIProxyAPI remains the sole authority for upstream accounts, OAuth sessions, credentials, quotas, health, retries, and failover.

## Environment and installation

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"

codex plugin marketplace add vai8havchoudhary/codex --ref main
codex plugin add cliproxy-models@cliproxy
codex plugin add codex-moa@cliproxy
```

The plugins never enumerate proxy account files and never print or persist the key value. Codex stores only the environment-variable name `CLIPROXY_API_KEY`.

## Modern Codex profiles

Codex 0.134.0 and later load the base configuration and then overlay a separate profile file. `cliproxy-models` 1.1.0 therefore maintains this seven-document state:

```text
~/.codex/config.toml
~/.codex/cliproxy-grok-4-6.config.toml
~/.codex/cliproxy-gemini-3-7-flash.config.toml
~/.codex/cliproxy-luna.config.toml
~/.codex/luna-grok.config.toml
~/.codex/grok-gemini.config.toml
~/.codex/cliproxy-council-models.json
```

The base file contains the single provider and selected top-level default `model` / `model_provider`. Each overlay contains top-level `model` and `model_provider`; named council overlays also bind root-only `developer_instructions` to the matching shared MoA policy. The plugin removes only its own managed legacy tables and never leaves a managed top-level `profile` selector or `[profiles.*]` table.

All changed documents form one backup-aware, mode-`0600`, atomic, post-validated transaction. Any partial write or validation failure restores exact original bytes and modes. Unmanaged collisions, malformed files, and symlinks fail before mutation.

## Exact alias setup

The authoritative VPS2 catalog contains:

```text
gpt-5.6-luna
gpt-5.6-luna-advisor
grok-4.6
gemini-3.7-flash-high
gemini-3.7-flash-advisor
```

There is no bare `gemini-3.7-flash`. Automatic Gemini selection must refuse. Choose an exact ID only when it is present in both CLIProxyAPI catalogs:

This seven-file two-council installation requires explicit `--gemini-model gemini-3.7-flash-high`. A different admitted Gemini alias, including `gemini-3.7-flash-advisor`, is refused before mutation because it cannot satisfy the advertised `grok-gemini` contract. Setup never silently substitutes High.

```text
@cliproxy-models Set up CLIProxyAPI models with --gemini-model gemini-3.7-flash-high and use Grok by default.
```

Modern profile usage after setup:

```bash
codex exec --profile cliproxy-luna 'Reply with LUNA_PROFILE_OK'
codex exec --profile cliproxy-grok-4-6 'Reply with GROK_PROFILE_OK'
codex exec --profile cliproxy-gemini-3-7-flash 'Reply with GEMINI_PROFILE_OK'
```

## Packaged dependency contract

`codex-moa/authority.json` binds the consumer to `cliproxy-models` 1.1.0 in both supported layouts:

```text
<repo>/plugins/codex-moa + <repo>/plugins/cliproxy-models
<cache>/cliproxy/codex-moa/2.0.0 + <cache>/cliproxy/cliproxy-models/1.1.0
```

The native preflight reads the base provider, three model overlays, and selected named council overlay. It selects only the exact pinned authority version and refuses missing, incompatible, malformed, or multiply located authorities.

## Native council

```text
$luna-grok Implement this repository task with Luna writing and Grok reviewing.
$grok-gemini Implement this repository task with Grok writing and Gemini High reviewing.
@codex-moa Resume checkpoint <handle>.
```

Start a matching root with `codex --profile luna-grok` or `codex --profile grok-gemini`. Skills cannot change the current root model. Exact `gpt-5.6-luna` must appear in both catalogs; `-advisor` is not a substitute. Gemini-led is unsupported and refused for new runs.

The policy uses repository localization, one accepted plan, one writer by default, opposite-model criticism at high-leverage gates, validation-led bounded recovery, independent final review, and compact immutable checkpoints. Schema-2 completion requires structured native reviewer witnesses and passing gates; witnesses are agent-submitted claims, so actual native event transcripts must be independently checked. Historical schema-1 records remain readable, not writable.

Council lifecycles differ: `luna-grok` retains read-only, tool-capable Grok advisors. In `grok-gemini`, Grok gathers source and Gemini **reviewed supplied evidence** only: a fresh single-turn plan critic and distinct fresh final reviewer receive complete bounded evidence in their initial prompts, use no tools or follow-ups, return actual verdicts and are closed. Each semantic gate allows one primary attempt plus at most one fresh transport retry; exhausted capability failures block. Final packets include the complete diff, relevant full resulting files, requirements, revision and executed gate results; if they cannot fit, stop rather than omit material evidence. Packet SHA-256 and native references are compact checkpoint evidence, not authenticated attestations. This policy does not fix or qualify Gemini tool/history continuation. Both schema-1 and shape-valid historical schema-2 digests remain readable; fresh-reviewer rules apply to new writes only.

## Evidence and release status

The pre-correction exact-main VPS2 provider/MCP/council evidence and the profile blocker are recorded in [`docs/VPS2_GATE_2026-08-30.md`](docs/VPS2_GATE_2026-08-30.md). That earlier PASS does not waive the need for a fresh exact-main reinstall/profile/council gate after this correction.

No `v2.0.0` release should be published until that final gate is adjudicated.

## Development validation

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
for suite in plugins/*/scripts plugins/*/tests; do
  if [[ -d "$suite" ]] && compgen -G "$suite/test_*.py" >/dev/null; then
    python3 -m unittest discover -s "$suite" -p 'test_*.py' -v
  fi
done
python3 -m compileall -q plugins tests
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 -m json.tool release.json >/dev/null
for manifest in plugins/*/.codex-plugin/plugin.json; do python3 -m json.tool "$manifest" >/dev/null; done
for contract in plugins/*/authority.json; do [[ -e "$contract" ]] || continue; python3 -m json.tool "$contract" >/dev/null; done
for mcp in plugins/*/.mcp.json; do [[ -e "$mcp" ]] || continue; python3 -m json.tool "$mcp" >/dev/null; done
git diff --check
```

See [SETUP.md](SETUP.md), [AGENTS.md](AGENTS.md), [agent.md](agent.md), [SECURITY.md](SECURITY.md), and [docs/RELEASING.md](docs/RELEASING.md).

## Stable native council catalog

Named council overlays own `model_catalog_json`, pointing at the transaction-managed `cliproxy-council-models.json` beside the base config. It contains the exact three admitted models with the original live Codex-catalog metadata; capabilities are never synthesized. The JSON ownership marker is `_codex_cliproxy_models: 1`. Unmanaged or malformed JSON, duplicates/missing models, unsafe paths, and concurrent changes fail closed. The seventh file shares backups, mode 0600, post-validation, idempotence and exact rollback with all six TOML documents.

This derived startup snapshot keeps native subagent model selection independent of mutable shared catalog-cache entries. It is not a second alias authority: preflight still reads both live proxy catalogs and refuses stale snapshot metadata. The base default is not pinned to this three-model snapshot, so an unrelated admitted default is preserved by `--default preserve`. Restart Codex after setup/catalog refresh.
