---
name: grok-gemini
description: Run a native Codex repository council with grok-4.6 writing and gemini-3.7-flash-high advising and reviewing. Use when the user requests the grok-gemini combination or starts its named profile.
---

Use the shared [codex-moa policy](../codex-moa/SKILL.md), read it fully, and bind `council` and `leader_mode` to `grok-gemini`. The actual root must be `grok-4.6`; the advisor/reviewer must be `gemini-3.7-flash-high`. A skill cannot switch the root model: on mismatch stop and ask to restart with `codex --profile grok-gemini`.

These leader duties apply only to the root session. A child retains its parent's explicit read-only assignment and model; it must not initiate another council. Follow the shared native capability, bounded single-writer, validation, review-witness, and checkpoint rules without duplicating orchestration.
