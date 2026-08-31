---
description: Run luna-grok with gpt-5.6-luna as the acting writer and grok-4.6 as native advisor/reviewer.
---

Use the `luna-grok` skill and its shared `codex-moa` policy. Confirm the actual root model matches `gpt-5.6-luna`, or stop and request `codex --profile luna-grok`. Establish actual native opposite-model responses before editing and require a returned final review verdict on the final diff. Child advisors remain read-only and do not inherit root coordination duties.
