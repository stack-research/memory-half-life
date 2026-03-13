# λ Memory Half-Life

An agent memory system where knowledge decays unless reinforced. Built on top of [entropy-os](https://github.com/stack-research/entropy-os).

Most AI agent memory systems accumulate indefinitely — context windows grow, vector stores bloat, nothing is ever removed. Memory Half-Life inverts that pattern. Memories have a half-life: their confidence degrades over time, and memories that go unused expire and are permanently forgotten. The agent stays lean by forgetting.

## How it works

Each memory has a **confidence score** that follows exponential decay:

```
confidence = 2^(-elapsed / half_life)
```

- At creation, confidence is `1.0` (full certainty).
- After one half-life, confidence drops to `0.5`.
- After two half-lives, `0.25`. And so on.
- When confidence falls below a threshold (default `0.1`), the memory expires.

**Recalling a memory resets the clock.** Memories that are actively used in reasoning get refreshed automatically — things you use survive. Things you ignore are forgotten. This mirrors how biological memory works: rehearsal strengthens traces, neglect lets them fade.

Time is measured in **ticks**, not wall-clock seconds. In an agent context, each conversation turn is a tick. This makes decay deterministic and testable.

## Installation

Requires Python >= 3.12 and [entropy-os](https://github.com/stack-research/entropy-os) as a sibling directory.

```bash
pip install -e ../entropy-os
pip install -e .
```

## Quick start

### As a library

```python
from memoryhalflife import MemoryEngine

eng = MemoryEngine(default_half_life=10)

# Store some memories
eng.store("user-name", "Alice")
eng.store("api-key", "sk-1234", half_life=5)  # shorter half-life, expires faster

# Advance time (e.g., conversation turns)
eng.tick(8)

# Recall refreshes the memory — it survives
user = eng.recall("user-name")
print(user.confidence(eng.now))  # 1.0 (just refreshed)

# Peek reads without refreshing — lets you check without affecting decay
api = eng.peek("api-key")
# api is None — it expired (half_life=5, threshold=0.1 → TTL ≈ 17 ticks...
# actually with half_life=5 and threshold=0.1, TTL = ceil(-5 * log2(0.1)) = 17)

# But with a shorter threshold:
eng2 = MemoryEngine(default_half_life=5, default_threshold=0.5)
eng2.store("temp", "short-lived")
eng2.tick(5)
print(eng2.peek("temp"))  # None — expired after exactly 5 ticks
```

### Key operations

| Method | Description |
|---|---|
| `store(key, content)` | Create or overwrite a memory |
| `recall(key)` | Read a memory **and refresh it** (implicit reinforcement) |
| `peek(key)` | Read a memory **without refreshing** (observation only) |
| `forget(key)` | Explicitly delete a memory |
| `tick(n)` | Advance time by `n` ticks |
| `memories()` | List all living memories |
| `fading(threshold)` | List memories below a confidence threshold |
| `entropy_score()` | Measure overall knowledge decay |
| `to_dict()` / `from_dict()` | Serialize and restore full state |

### Interactive REPL

```bash
memory-half-life
```

```
memory-half-life REPL  (type 'help' for commands)

[tick 0] > store weather It is sunny today
Stored: weather (half_life=10, ttl=34)

[tick 0] > store meeting Standup at 9am
Stored: meeting (half_life=10, ttl=34)

[tick 0] > tick 15
Advanced 15 tick(s) → now at tick 15

[tick 15] > list
2 memories:
  meeting: 'Standup at 9am'
    confidence=[######..............] 35.4%  half_life=10  accesses=0
  weather: 'It is sunny today'
    confidence=[######..............] 35.4%  half_life=10  accesses=0

[tick 15] > recall weather
Recalled (refreshed):
  weather: 'It is sunny today'
    confidence=[####################] 100.0%  half_life=10  accesses=1

[tick 15] > tick 20
Advanced 20 tick(s) → now at tick 35

[tick 35] > list
1 memories:
  weather: 'It is sunny today'
    confidence=[#####...............] 25.0%  half_life=10  accesses=1
```

The meeting memory expired because it was never recalled. The weather memory survived because recalling it at tick 15 reset its decay clock.

## Architecture

```
memory-half-life/
├── src/memoryhalflife/
│   ├── __init__.py        # public API: MemoryEngine, Memory
│   ├── memory.py          # Memory dataclass, decay math
│   ├── engine.py          # MemoryEngine (wraps entropyos runtime)
│   └── cli.py             # interactive REPL
├── tests/
│   ├── test_memory.py     # decay math, serialization
│   └── test_engine.py     # store/recall/tick/expiry/reinforcement
└── pyproject.toml
```

### Relationship to entropy-os

Memory Half-Life imports `entropyos` as a dependency — it doesn't fork or vendor it. The `MemoryEngine` wraps an `EntropyRuntime` and stores memories in its `TTLStore`. The TTL for each memory is derived from its half-life and confidence threshold:

```
TTL = ceil(-half_life * log2(threshold))
```

This means entropy-os handles the actual expiry mechanics (tick evaluation, state cleanup, serialization) while memory-half-life adds the confidence decay model and agent-oriented API on top.

## Design decisions

- **Continuous confidence + binary expiry.** Confidence is a smooth gradient (useful for ranking, prioritization, deciding what to reinforce). But actual removal is binary — once confidence drops below the threshold, the memory is gone. This gives the agent a gradient to reason over, not just alive/dead.

- **Ticks, not wall-clock time.** One tick = one conversation turn (or whatever event you want to map it to). Makes the system deterministic, testable, and independent of real-world timing.

- **Recall refreshes, peek doesn't.** `recall()` is the "this memory is relevant right now" signal — it resets the decay clock. `peek()` lets you inspect without side effects. This mirrors entropy-os's `touch()` pattern.

- **No accumulation.** There's no unbounded growth. Memories that aren't reinforced disappear. The agent's knowledge is bounded by relevance, not by storage limits.

## Running tests

```bash
pytest
```
