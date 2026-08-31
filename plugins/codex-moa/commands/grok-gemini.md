---
description: Run grok-gemini with grok-4.6 as the acting writer and gemini-3.7-flash-high as native advisor/reviewer.
---

Use the `grok-gemini` skill and its shared `codex-moa` policy. Confirm the actual root model matches `grok-4.6`, or stop and request `codex --profile grok-gemini`. Establish actual native opposite-model responses before editing and require a returned final review verdict on the final diff. Child advisors remain read-only and do not inherit root coordination duties.

Grok gathers source; Gemini reviewed supplied evidence only. Use fresh single-turn native plan criticism and a distinct fresh final reviewer, each with complete bounded evidence in the INITIAL prompt. NO tools, READY reservation, send_input, follow-ups or history reuse. Await the verdict and close; follow the shared per-gate transport budget and stop rules.
