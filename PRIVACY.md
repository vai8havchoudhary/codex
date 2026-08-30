# Privacy

These are local Codex plugins. They do not operate a hosted service and do not collect telemetry.

`cliproxy-models` contacts only the endpoint selected through `CLIPROXY_URL`. It reads `CLIPROXY_API_KEY` from the current process environment for authenticated catalog requests, never prints its value, and never writes its value to Codex configuration. Codex stores only the environment-variable name.

`codex-moa` coordinates native Codex agents. Its checkpoint MCP server stores compact execution records locally beneath `CODEX_HOME`; it receives no proxy key and rejects credentials, account data, cookies, tokens, and environment dumps. Checkpoints may contain repository paths, commands, validation summaries, decisions, and risks supplied by the active Codex session.

CLIProxyAPI, Codex, and upstream model providers remain subject to their own privacy terms.
