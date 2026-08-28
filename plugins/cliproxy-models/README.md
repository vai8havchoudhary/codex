# CLIProxyAPI Models plugin

This plugin configures one Codex provider and two model profiles:

- `cliproxy-grok-4-6`
- `cliproxy-gemini-3-7-flash`

Required launch environment:

```bash
export CLIPROXY_URL=http://127.0.0.1:8317
export CLIPROXY_API_KEY="$(<"$HOME/.cli-proxy-api/.proxy-api-key")"
```

Invoke the `cliproxy-models` skill for setup, diagnosis, or model switching. The implementation uses only the Python standard library and never reads CLIProxyAPI upstream account files.
