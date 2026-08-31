---
description: Perform an independent opposite-model final review of a native Codex MoA implementation.
---

Use the shared `codex-moa` review phase and the retained independent read-only verifier on the exact opposite model. Give it the final diff/revision and executed gate evidence; require an actual returned APPROVE or REQUEST_CHANGES verdict. Store either verdict unchanged in the native reviewer witness. REQUEST_CHANGES is valid review evidence but must prevent completion until material findings are resolved, affected gates rerun, and a new returned APPROVE covers the final revision. Follow the shared bounded fallback policy if the retained verifier is unavailable.
