"""Demo CLI / REPL for memory-half-life.

A simple interactive loop that lets you store, recall, and observe memories
decaying over conversation turns.
"""

from __future__ import annotations

import json
import sys

from .engine import MemoryEngine


HELP = """\
Commands:
  store <key> <content>     Store a memory (default half-life)
  recall <key>              Recall a memory (refreshes it)
  peek <key>                Read a memory without refreshing
  forget <key>              Explicitly forget a memory
  list                      Show all living memories with confidence
  fading                    Show memories below 50% confidence
  tick [n]                  Advance time by n ticks (default 1)
  entropy                   Show entropy score
  state                     Dump full state as JSON
  help                      Show this help
  quit                      Exit
"""


def _format_memory(mem, now: int) -> str:
    conf = mem.confidence(now)
    bar_len = int(conf * 20)
    bar = "#" * bar_len + "." * (20 - bar_len)
    tags = f"  tags={list(mem.tags)}" if mem.tags else ""
    return (
        f"  {mem.key}: {mem.content!r}\n"
        f"    confidence=[{bar}] {conf:.1%}  "
        f"half_life={mem.half_life}  accesses={mem.access_count}{tags}"
    )


def main() -> int:
    eng = MemoryEngine()
    print("memory-half-life REPL  (type 'help' for commands)\n")

    while True:
        try:
            line = input(f"[tick {eng.now}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not line:
            continue

        parts = line.split(maxsplit=2)
        cmd = parts[0].lower()

        if cmd in ("quit", "exit", "q"):
            return 0

        elif cmd == "help":
            print(HELP)

        elif cmd == "store":
            if len(parts) < 3:
                print("Usage: store <key> <content>")
                continue
            mem = eng.store(parts[1], parts[2])
            print(f"Stored: {mem.key} (half_life={mem.half_life}, ttl={mem.ttl()})")

        elif cmd == "recall":
            if len(parts) < 2:
                print("Usage: recall <key>")
                continue
            mem = eng.recall(parts[1])
            if mem is None:
                print(f"'{parts[1]}' — not found or expired (forgotten)")
            else:
                print(f"Recalled (refreshed):\n{_format_memory(mem, eng.now)}")

        elif cmd == "peek":
            if len(parts) < 2:
                print("Usage: peek <key>")
                continue
            mem = eng.peek(parts[1])
            if mem is None:
                print(f"'{parts[1]}' — not found or expired (forgotten)")
            else:
                print(f"Peeked (not refreshed):\n{_format_memory(mem, eng.now)}")

        elif cmd == "forget":
            if len(parts) < 2:
                print("Usage: forget <key>")
                continue
            if eng.forget(parts[1]):
                print(f"Forgot '{parts[1]}'")
            else:
                print(f"'{parts[1]}' — not found")

        elif cmd == "list":
            mems = eng.memories()
            if not mems:
                print("No memories.")
            else:
                now = eng.now
                print(f"{len(mems)} memories:")
                for m in mems:
                    print(_format_memory(m, now))

        elif cmd == "fading":
            fading = eng.fading()
            if not fading:
                print("No fading memories.")
            else:
                now = eng.now
                print(f"{len(fading)} fading memories:")
                for m in fading:
                    print(_format_memory(m, now))

        elif cmd == "tick":
            n = int(parts[1]) if len(parts) > 1 else 1
            events = eng.tick(n)
            print(f"Advanced {n} tick(s) → now at tick {eng.now}")

        elif cmd == "entropy":
            score = eng.entropy_score()
            print(json.dumps(score, indent=2))

        elif cmd == "state":
            print(json.dumps(eng.to_dict(), indent=2))

        else:
            print(f"Unknown command: {cmd}  (type 'help')")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
