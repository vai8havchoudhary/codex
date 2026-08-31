---
description: Switch the default for new Codex sessions to exact gpt-5.6-luna through the guarded model setup transaction.
---

Use the `cliproxy-models` skill and bundled `scripts/plugin.py` with the explicit Gemini alias and `use luna`. Require `gpt-5.6-luna` in both catalogs; never substitute `gpt-5.6-luna-advisor`. This selects standalone Luna, not a council; use `codex --profile luna-grok` for MoA.
