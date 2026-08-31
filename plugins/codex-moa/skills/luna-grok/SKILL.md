---
name: luna-grok
description: Run a native Codex repository council with gpt-5.6-luna writing and grok-4.6 advising and reviewing. Use when the user requests the luna-grok combination or starts its named profile.
---

Use the shared [codex-moa policy](../codex-moa/SKILL.md), read it fully, and bind `council` and `leader_mode` to `luna-grok`. The actual root must be `gpt-5.6-luna`; the advisor/reviewer must be `grok-4.6`. A skill cannot switch the root model: on mismatch stop and ask to restart with `codex --profile luna-grok`.

These leader duties apply only to the root session. A child retains its parent's explicit read-only assignment and model; it must not initiate another council. Follow the shared native capability, bounded single-writer, validation, review-witness, and checkpoint rules without duplicating orchestration.

Use the shared Luna retained-agent policy unchanged: Grok may use read-only tools, the localizer is reused for plan criticism, and the reserved reviewer handles final review. The Gemini single-turn evidence-only restriction does not apply to this council.
