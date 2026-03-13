# Memory Half-Life for AI Agents

A standalone project that builds a real application on top of [entropy-os](../entropy-os/) — demonstrating decay as a load-bearing architectural feature, not just a demo.

## What this is

An agent memory system where context and knowledge literally decay unless refreshed. Connects entropy-os (decaying software) with AI agent memory management.

## Why it's a separate project

This lives outside entropy-os intentionally. It proves entropy-os is a dependency you plug in, not a monolith you extend. A blog post lands harder when the reader can see a standalone repo with `entropy-os` in its `pyproject.toml` dependencies. Any project could do the same.

## Architecture

```
memory-half-life/
├── src/memoryhalflife/
│   ├── __init__.py
│   ├── engine.py          # core memory engine (uses entropyos runtime)
│   ├── memory.py          # Memory dataclass, confidence decay model
│   └── cli.py             # demo CLI or REPL
├── tests/
├── pyproject.toml         # depends on entropy-os
├── blog/
│   └── memory-half-life.md
└── CLAUDE.md              # this file
```

The dependency relationship: `memory-half-life` imports `entropyos`, creates a runtime, and builds the memory system on top of TTLStore + the decay model. It doesn't fork or vendor — it uses the public API.

## Design decisions

These were discussed and agreed upon before building:

- **Continuous half-life** with a confidence score that decays, plus binary expiry when confidence drops below a threshold — gives the agent a gradient to reason over, not just alive/dead.
- **Conversation turn as tick trigger** — natural, observable, easy to instrument.
- **Implicit reinforcement via access** — memories used in reasoning get refreshed automatically, matching entropy-os's existing `touch()` pattern.
- **Extension module** that imports entropy-os as a dependency — proves the plug-in model.

## Core concept

- Agent memories (facts, observations, conversation history) are stored with TTL in the entropy-os state store.
- Each memory has a half-life: its confidence/weight degrades over ticks.
- Memories that are accessed (used in reasoning) get their TTL refreshed — things the agent actively uses survive.
- Memories that go untouched expire and are permanently forgotten.
- The agent must decide what to reinforce and what to let go.
- Entropy score measures how much of the agent's knowledge is decaying vs. active.

## Why this matters

Most AI agent memory systems accumulate indefinitely — context windows grow, vector stores bloat, nothing is ever removed. This inverts that pattern. The agent's memory is bounded not by token limits but by relevance decay. Old, unused knowledge disappears. The agent stays lean by forgetting.

## Blog post

The narrative: "here's a 200-line project that gives AI agents the ability to forget" with entropy-os doing the heavy lifting underneath. Draft lives in `blog/memory-half-life.md`.

## Build notes

- Python >=3.12, no external deps beyond entropy-os
- entropy-os is installed as a path dependency: `entropy-os = {path = "../entropy-os", editable = true}`
- Follow entropy-os conventions: deterministic, pure core, explicit time, no wall-clock, canonical JSON
- Tests with pytest, same style as entropy-os
