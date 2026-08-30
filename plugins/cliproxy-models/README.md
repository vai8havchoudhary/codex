# CLIProxyAPI Models plugin

This plugin configures one Codex provider and two exact model profiles:

- `cliproxy-grok-4-6`
- `cliproxy-gemini-3-7-flash`

Required launch environment:

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Invoke the `cliproxy-models` skill for setup, diagnosis, or model switching. The implementation uses only the Python standard library and never reads CLIProxyAPI upstream account files.

See the repository guides:

- [Setup and troubleshooting](../../SETUP.md)
- [Security policy](../../SECURITY.md)
- [Agent handbook](../../agent.md)
- [Release procedure](../../docs/RELEASING.md)

## Current VPS2 alias ambiguity

A live VPS2 catalog may expose `grok-4.6` plus both `gemini-3.7-flash-high` and `gemini-3.7-flash-advisor`, with no bare `gemini-3.7-flash`. Automatic setup intentionally refuses that catalog because selecting either Gemini route would be policy, not discovery.

Choose one exact alias explicitly only after deciding which route you intend:

```bash
python3 scripts/plugin.py \
  --gemini-model gemini-3.7-flash-high \
  setup grok
```

The explicit alias must still be present in both the OpenAI-compatible and Codex-compatible CLIProxyAPI catalogs. No account file or key value is inspected.
