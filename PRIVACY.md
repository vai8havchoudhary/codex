# Privacy

CLIProxyAPI Models is a local Codex plugin. It does not operate a hosted service and does not collect telemetry.

The setup utility contacts only the endpoint selected through `CLIPROXY_URL`. It reads `CLIPROXY_API_KEY` from the current process environment for authenticated requests, never prints its value, and never writes its value to Codex configuration. Codex stores only the environment-variable name.

CLIProxyAPI and upstream model providers remain subject to their own privacy terms.
