---
name: grok-gemini
description: Run a native Codex repository council with grok-4.6 writing and gemini-3.7-flash-high advising and reviewing. Use when the user requests the grok-gemini combination or starts its named profile.
---

Use the shared [codex-moa policy](../codex-moa/SKILL.md), read it fully, and bind `council` and `leader_mode` to `grok-gemini`. The actual root must be `grok-4.6`; the advisor/reviewer must be `gemini-3.7-flash-high`. A skill cannot switch the root model: on mismatch stop and ask to restart with `codex --profile grok-gemini`.

These leader duties apply only to the root session. A child retains its parent's explicit read-only assignment and model; it must not initiate another council. Follow the shared native capability, bounded single-writer, validation, review-witness, and checkpoint rules without duplicating orchestration.

Read the shared Grok-to-Gemini single-turn evidence-only section before acting. Grok gathers source; Gemini reviewed supplied evidence, with NO tools, READY reservation, send_input, follow-ups or history reuse. Use a fresh initial-prompt plan critic and a distinct fresh final reviewer; await each actual verdict and close. Follow the shared complete-packet, packet SHA-256 and finite per-gate transport rules; stop blocked rather than omitting evidence or restarting failed gates indefinitely.
