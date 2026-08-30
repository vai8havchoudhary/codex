# Research basis for the native Codex MoA policy

This plugin applies research findings as bounded engineering rules rather than reproducing any paper's full runtime.

## Repository localization and environment feedback

- **SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering** — https://arxiv.org/abs/2405.15793
- **Agentless: Demystifying LLM-based Software Engineering Agents** — https://arxiv.org/abs/2407.01489

Derived rules: localize before editing; use repository-native commands and tests as authoritative feedback; avoid extra agent machinery when a simple localized repair suffices.

## Planning and modular specialization

- **CodePlan: Repository-level Coding using LLMs and Planning** — https://arxiv.org/abs/2309.12499
- **MASAI: Modular Architecture for Software-engineering AI Agents** — https://arxiv.org/abs/2406.11638

Derived rules: maintain one accepted dependency-aware plan; assign agents bounded roles; avoid unnecessarily long shared trajectories; give writing workers explicit non-overlapping ownership.

## Model diversity and aggregation

- **Mixture-of-Agents Enhances Large Language Model Capabilities** — https://arxiv.org/abs/2406.04692

Derived rule: ask different models for independent evidence or criticism at high-leverage decision points, then synthesize into one acting trajectory. Continuous debate after every tool call is intentionally rejected for latency, cost, and patch-coherence reasons.

## Feedback-driven repair and durable memory

- **Reflexion: Language Agents with Verbal Reinforcement Learning** — https://arxiv.org/abs/2303.11366

Derived rules: open recovery only after concrete environment feedback; preserve compact failure evidence and decisions; bound retries; resume from an external checkpoint plus fresh repository inspection rather than replaying the entire conversation.

## Native Codex alignment

The current Codex multi-agent surface supports named subagents, model overrides, bounded history forks, messaging, follow-up tasks, waiting, interruption, and closure. The plugin uses those primitives directly and adds only a narrow checkpoint MCP server. It does not implement a competing scheduler or model gateway.
