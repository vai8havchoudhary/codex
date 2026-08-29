# Setup and operations

This guide installs and operates both plugins in the `cliproxy` Codex marketplace.

## 1. Prerequisites

Shared requirements:

- Codex with `codex plugin` marketplace commands;
- Python 3.11 or newer;
- CLIProxyAPI at a loopback HTTP endpoint or remote HTTPS endpoint;
- a CLIProxyAPI access key;
- exact Grok 4.6 and Gemini 3.7 Flash aliases exported by CLIProxyAPI.

`hermes-moa` additionally requires Hermes Agent with working `hermes config` and `hermes moa` commands. Configure and authenticate all upstream model accounts in CLIProxyAPI before using either plugin.

## 2. Launch environment

For the standard local proxy:

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Confirm presence without revealing values:

```bash
test -n "${CLIPROXY_URL:-}" && echo "CLIPROXY_URL is set"
test -n "${CLIPROXY_API_KEY:-}" && echo "CLIPROXY_API_KEY is set"
```

Do not echo the key, enable shell tracing around it, commit it, or paste it into Codex/Hermes configuration. Applications launched from Finder or another launcher may not inherit terminal exports; configure the same launch environment and fully restart the application.

Remote proxies must use HTTPS:

```bash
export CLIPROXY_URL=https://proxy.example.com
```

Plain HTTP is rejected unless the host is `localhost`, `127.0.0.1`, or `::1`.

## 3. Marketplace installation

```bash
codex plugin marketplace add vai8havchoudhary/codex --ref main
codex plugin list --marketplace cliproxy --available --json
```

Install the desired plugins:

```bash
codex plugin add cliproxy-models@cliproxy
codex plugin add hermes-moa@cliproxy
```

## 4. Configure Codex models

Use Grok by default:

```text
@cliproxy-models Set up CLIProxyAPI models and use Grok 4.6 by default.
```

Use Gemini by default:

```text
@cliproxy-models Set up CLIProxyAPI models and use Gemini 3.7 Flash by default.
```

The plugin validates endpoint safety, key presence, both model catalogs, exact aliases, provider/profile collisions, and generated TOML before writing. It creates one Codex provider `cliproxyapi` and profiles `cliproxy-grok-4-6` and `cliproxy-gemini-3-7-flash`. Codex stores only:

```toml
env_key = "CLIPROXY_API_KEY"
```

Fully restart Codex Desktop and start a new thread after setup or switching.

Direct commands from a checkout:

```bash
python3 plugins/cliproxy-models/scripts/plugin.py status
python3 plugins/cliproxy-models/scripts/plugin.py setup grok
python3 plugins/cliproxy-models/scripts/plugin.py use gemini
```

## 5. Configure Hermes Mixture of Agents

Verify Hermes first:

```bash
hermes --version
hermes moa list
```

Choose which model acts as the aggregator. The other exact model becomes its reference advisor.

Grok acts, Gemini advises:

```text
@hermes-moa Set up Hermes MoA with Grok leading.
```

Gemini acts, Grok advises:

```text
@hermes-moa Set up Hermes MoA with Gemini leading.
```

The plugin creates one Hermes provider:

```yaml
providers:
  cliproxy:
    name: CLIProxyAPI
    api: http://127.0.0.1:8317/v1
    key_env: CLIPROXY_API_KEY
    transport: openai_chat
```

It also creates:

```text
cliproxy-grok-led     Gemini reference -> Grok aggregator
cliproxy-gemini-led   Grok reference   -> Gemini aggregator
```

Default tuning follows Hermes' cost-conscious MoA shape:

```yaml
reference_max_tokens: 600
max_tokens: 4096
fanout: user_turn
privacy_filter: display
enabled: true
```

An existing `privacy_filter: full` is preserved. `display` redacts user-visible/traced advisor text while leaving raw advice available to the aggregator; `full` also redacts the text passed to the aggregator.

Direct commands:

```bash
python3 plugins/hermes-moa/scripts/plugin.py status
python3 plugins/hermes-moa/scripts/plugin.py setup grok-led
python3 plugins/hermes-moa/scripts/plugin.py setup gemini-led
python3 plugins/hermes-moa/scripts/plugin.py use grok-led
python3 plugins/hermes-moa/scripts/plugin.py use gemini-led
```

Optional tuning:

```bash
python3 plugins/hermes-moa/scripts/plugin.py setup grok-led \
  --reference-max-tokens 700 \
  --max-tokens 4096 \
  --fanout every_n:2 \
  --privacy-filter full
```

Supported fan-out values are `user_turn`, `per_iteration`, and `every_n:<N>` where `N >= 2`. `user_turn` runs advisors once per user turn; `per_iteration` reruns them on every tool-loop iteration and costs more.

Use a named Hermes profile without changing the default profile:

```bash
python3 plugins/hermes-moa/scripts/plugin.py \
  --profile coder \
  setup gemini-led
```

After setup, use Hermes directly:

```text
/model cliproxy-grok-led --provider moa
/model cliproxy-gemini-led --provider moa
/moa <one-shot prompt using the configured default preset>
```

The acting aggregator writes the final response and performs tool calls. Restart Hermes or start a new Hermes session after configuration changes.

## 6. Exact alias ambiguity

When CLIProxyAPI intentionally exports multiple matching aliases, pass exact IDs:

```bash
python3 plugins/hermes-moa/scripts/plugin.py \
  --grok-model 'EXACT_GROK_4_6_ALIAS' \
  --gemini-model 'EXACT_GEMINI_3_7_FLASH_ALIAS' \
  setup grok-led
```

The same flags are available in `cliproxy-models`. Explicit IDs must still exist in both catalogs and match the exact family/version contract.

## 7. Status and diagnosis

Codex prompts:

```text
@cliproxy-models Check my CLIProxyAPI model setup.
@hermes-moa Check my Hermes MoA configuration.
```

A Hermes status check is read-only. Exit status 2 reports missing or mismatched custody paths and does not write configuration.

## 8. Backups and rollback

Codex changes create timestamped `~/.codex/config.toml.bak.*` files. Hermes changes to an existing config create:

```text
~/.hermes/config.yaml.bak.cliproxy-moa.<timestamp>
```

For a named profile, the backup is under `~/.hermes/profiles/<profile>/`. A failed Hermes mutation restores exact original bytes automatically; a partial newly created file is removed.

Manual restoration:

```bash
cp "$HOME/.hermes/config.yaml.bak.cliproxy-moa.<timestamp>" \
   "$HOME/.hermes/config.yaml"
chmod 600 "$HOME/.hermes/config.yaml"
```

Restart the affected application after restoring.

## 9. Upgrade

```bash
codex plugin marketplace upgrade cliproxy
codex plugin list --marketplace cliproxy --json
```

Refresh the installed plugin through Codex, read [CHANGELOG.md](CHANGELOG.md), and rerun its status command. Setup is byte-idempotent when the desired values already match.

## 10. Uninstall

```bash
codex plugin remove hermes-moa@cliproxy
codex plugin remove cliproxy-models@cliproxy
```

Optionally remove the marketplace:

```bash
codex plugin marketplace remove cliproxy
```

Plugin removal does not erase application configuration previously written. Restore a pre-install backup or remove only the owned provider/profile/preset entries while the application is stopped.

## 11. Troubleshooting

### Key is unset or requests return 401/403

Reload the key without printing it and ensure both applications inherited it.

### Exact alias is absent or ambiguous

Publish one stable exact alias per model in CLIProxyAPI, or pass explicit exact IDs. No nearby model version is substituted.

### Hermes MoA surface is unavailable

Upgrade Hermes Agent until both `hermes moa list` and `hermes config get ... --json` work. The plugin refuses to edit a Hermes installation without the built-in MoA surface.

### Foreign provider or preset collision

Inspect `providers.cliproxy`, `moa.presets.cliproxy-grok-led`, and `moa.presets.cliproxy-gemini-led`. Setup refuses foreign data. Use `--force` only after deciding replacement is safe.

### HTTP endpoint rejected

Use loopback HTTP or remote HTTPS. URLs with embedded credentials, query strings, fragments, or paths other than `/v1` are rejected.

## 12. Development checkout

```bash
git clone https://github.com/vai8havchoudhary/codex.git
cd codex
python3 -m unittest discover -s tests -p 'test_*.py' -v
for suite in plugins/*/scripts; do
  python3 -m unittest discover -s "$suite" -p 'test_*.py' -v
done
python3 -m compileall -q plugins tests
```

Use synthetic fixtures only. Never use a real key value in tests or logs.
