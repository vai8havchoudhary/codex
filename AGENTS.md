# Repository instructions

This repository is a Codex plugin marketplace, not a Codex source fork.

- Keep the marketplace entry, plugin folder, and manifest name equal to `cliproxy-models`.
- Never commit CLIProxyAPI API-key values or upstream account data.
- Preserve one provider: CLIProxyAPI owns multi-account routing; Codex stores only endpoint, environment-variable name, and stable aliases.
- Require exact Grok 4.6 and Gemini 3.7 Flash aliases in both provider catalogs.
- Keep configuration writes fail closed, atomic, backed up, and idempotent.
- Run the validation commands in `README.md` after every change.
