# Security policy

## Reporting

Do not open a public issue containing API keys, account identifiers, local configuration/profile contents, model-catalog snapshots, checkpoint contents, backup contents, or exploit details. Prefer a private GitHub security advisory and never include the value of `CLIPROXY_API_KEY`.

## Model and credential authority

- CLIProxyAPI owns upstream accounts, credentials, quota, retries, health, and failover.
- `cliproxy-models` stores the endpoint, exact admitted IDs, stable profile names, root-only council instructions, and `env_key = "CLIPROXY_API_KEY"`. The API-key value is used only for authenticated catalog requests; it is not added to local configuration or the derived catalog.
- The derived catalog retains the selected models' full live Codex descriptors, including capabilities and model instructions, unchanged. It does not read account files or synthesize capabilities. This server-supplied metadata is not a credential store or a general-purpose redaction boundary; inspect it before sharing.
- Plain HTTP is loopback-only.
- Exact aliases must exist in both catalogs; ambiguity requires explicit selection. Luna is exactly `gpt-5.6-luna`, never an `-advisor` substitute.
- No plugin reads or enumerates proxy account files.

## Seven-file configuration transaction

`cliproxy-models` 1.1.0 manages six TOML documents and one derived JSON catalog:

```text
~/.codex/config.toml
~/.codex/cliproxy-grok-4-6.config.toml
~/.codex/cliproxy-gemini-3-7-flash.config.toml
~/.codex/cliproxy-luna.config.toml
~/.codex/luna-grok.config.toml
~/.codex/grok-gemini.config.toml
~/.codex/cliproxy-council-models.json
```

These paths are relative to the selected base config's parent; the list shows the default location.

Named overlays own `developer_instructions` and `model_catalog_json`. Leader obligations apply only to the root; child advisors retain their explicitly assigned read-only role and opposite model. The catalog pointer pins live-derived native model metadata independently of the mutable shared cache. The base default is not pinned to this three-model snapshot. Preflight remains bound to both live proxy catalogs and refuses stale metadata: the snapshot is not a second admission authority.

Security properties apply to all seven transaction paths:

- no managed legacy profile selector/table;
- parse and ownership validation before mutation;
- symlink/non-regular-file and concurrent-change refusal;
- unmanaged overlay `model`/`model_provider` collision refusal, plus instruction/catalog-pointer collision refusal for named overlays;
- catalog ownership marker `_codex_cliproxy_models: 1`, exact selected model IDs, and malformed/duplicate/missing metadata refusal;
- coordinated timestamped mode-`0600` backups;
- atomic temporary-file replacements with fsync;
- whole-state post-validation;
- exact byte/mode rollback and partial-file cleanup on failure;
- byte/mode idempotence with no backup churn.

## Native council and checkpoints

- `codex-moa` uses only Codex's native subagent/tool runtime; it does not implement a second model loop, scheduler, or gateway.
- Supported directions are `luna-grok`: `gpt-5.6-luna` writes, `grok-4.6` advises/reviews; and `grok-gemini`: `grok-4.6` writes, `gemini-3.7-flash-high` advises/reviews.
- Gemini-led new runs are unsupported. Configuration admission does not prove native delegation; actual opposite-model spawn and returned-response evidence are required.
- One writer is the default; read-only localization/criticism is reused, a proven read-only reviewer is retained, and recovery is bounded and evidence-driven.
- The checkpoint MCP receives only `CODEX_HOME`, cannot call models or execute commands, rejects forbidden sensitive fields/recognizable secret-value patterns, and stores immutable mode-`0600` records beneath a mode-`0700` directory. It is not a general-purpose secret redactor.
- Schema-2 writes bind council/leader/advisor identity and require a returned final reviewer approval plus passing validation for completion. Native witnesses contain actual agent IDs, exact model IDs, verdicts, response summaries, transcript references and reviewed revisions.
- These local evidence claims are not authenticated attestations. A checksum establishes stored payload integrity, not that an agent actually ran or approved the final patch. Independently verify native runtime events, model identities, returned verdicts and the final revision; never treat self-reported approval as proof.
- Schema-1 historical records remain read-only, including unsupported historical Gemini-led records. Resumption requires a new schema-2 run and fresh capability/review gates; readable history is not a qualification pass.

## Release authority

Releases package tracked source directly and exclude local base/profile files, derived model-catalog snapshots, proxy keys, checkpoints, backups, caches, bootstrap payloads, Hermes sources, and generated output.

## Local hardening

For an existing default-location installation, check that these targets are regular non-symlink files before changing modes. If a different base config was selected, use its actual parent instead of the default path:

```bash
chmod 600 "$HOME/.cli-proxy-api/.proxy-api-key"
chmod 600 "$HOME/.codex/config.toml"
chmod 600 "$HOME/.codex/cliproxy-grok-4-6.config.toml"
chmod 600 "$HOME/.codex/cliproxy-gemini-3-7-flash.config.toml"
chmod 600 "$HOME/.codex/cliproxy-luna.config.toml"
chmod 600 "$HOME/.codex/luna-grok.config.toml"
chmod 600 "$HOME/.codex/grok-gemini.config.toml"
chmod 600 "$HOME/.codex/cliproxy-council-models.json"
chmod 700 "${CODEX_HOME:-$HOME/.codex}/codex-moa"
chmod 700 "${CODEX_HOME:-$HOME/.codex}/codex-moa/checkpoints"
```

Keep shell tracing disabled while exporting the key. Never put expanded secrets in dotfiles, arguments, checkpoints, logs, or reports. Review local descriptors/instructions and witness references before sharing them; protected file modes do not make their contents safe to publish.
