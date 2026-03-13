"""Core memory engine — built on top of entropyos runtime.

MemoryEngine is the main interface. It wraps an EntropyRuntime and provides
store/recall/tick/forget operations. Memories decay over ticks; accessing a
memory refreshes it (implicit reinforcement).
"""

from __future__ import annotations

from entropyos import EntropyRuntime
from entropyos.errors import ExpiredStateError

from .memory import DEFAULT_CONFIDENCE_THRESHOLD, DEFAULT_HALF_LIFE, Memory


def _store_key(key: str) -> str:
    """Prefix a memory key for the TTLStore namespace."""
    return f"mem/{key}"


class MemoryEngine:
    """Agent memory system with half-life decay.

    Wraps an EntropyRuntime. Memories are stored in its TTLStore with TTLs
    derived from their half-life and confidence threshold. Each tick advances
    decay; accessing a memory refreshes its TTL (touch pattern).
    """

    def __init__(
        self,
        runtime: EntropyRuntime | None = None,
        *,
        default_half_life: int = DEFAULT_HALF_LIFE,
        default_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        grace_ticks: int = 0,
    ) -> None:
        self._runtime = runtime or EntropyRuntime(grace_ticks=grace_ticks)
        self.default_half_life = default_half_life
        self.default_threshold = default_threshold

    @property
    def runtime(self) -> EntropyRuntime:
        return self._runtime

    @property
    def now(self) -> int:
        return self._runtime.clock.now()

    # -- Core operations --

    def store(
        self,
        key: str,
        content: str,
        *,
        half_life: int | None = None,
        tags: tuple[str, ...] = (),
        threshold: float | None = None,
    ) -> Memory:
        """Store a new memory (or overwrite an existing one)."""
        hl = half_life if half_life is not None else self.default_half_life
        th = threshold if threshold is not None else self.default_threshold
        now = self.now

        mem = Memory(
            key=key,
            content=content,
            half_life=hl,
            created_at=now,
            last_accessed_at=now,
            access_count=0,
            tags=tags,
            threshold=th,
        )
        self._put(mem)
        return mem

    def recall(self, key: str) -> Memory | None:
        """Recall a memory by key. Returns None if expired or missing.

        Implicitly refreshes the memory (touch pattern) — recalling a memory
        is evidence it's still relevant.
        """
        mem = self._get(key)
        if mem is None:
            return None
        # Touch: refresh access time and re-store with fresh TTL.
        refreshed = mem.touched(self.now)
        self._put(refreshed)
        return refreshed

    def peek(self, key: str) -> Memory | None:
        """Read a memory without refreshing it. No implicit reinforcement."""
        return self._get(key)

    def forget(self, key: str) -> bool:
        """Explicitly forget a memory. Returns True if it existed."""
        store_key = _store_key(key)
        try:
            self._runtime.store.get(store_key)
        except (ExpiredStateError, KeyError):
            return False
        # Overwrite with TTL=0 so it expires immediately on next access.
        self._runtime.store.set(store_key, {}, ttl_ticks=0)
        return True

    def tick(self, n: int = 1) -> list:
        """Advance time by n ticks. Returns scheduler events."""
        return self._runtime.tick(n=n)

    # -- Query operations --

    def memories(self) -> list[Memory]:
        """Return all living memories, sorted by key. Does not refresh them."""
        result = []
        for sk in self._runtime.store.keys():
            if not sk.startswith("mem/"):
                continue
            try:
                data = self._runtime.store.get(sk)
            except ExpiredStateError:
                continue
            if not data:  # empty dict from forget()
                continue
            result.append(Memory.from_dict(data))
        return sorted(result, key=lambda m: m.key)

    def fading(self, warn_threshold: float = 0.5) -> list[Memory]:
        """Return memories whose confidence is below the warning threshold."""
        now = self.now
        return [m for m in self.memories() if m.is_fading(now, warn_threshold)]

    def entropy_score(self) -> dict:
        """Proxy to the runtime's entropy score."""
        return self._runtime.entropy_score()

    # -- Serialization --

    def to_dict(self) -> dict:
        """Serialize full state (delegates to runtime)."""
        return self._runtime.to_dict()

    @classmethod
    def from_dict(
        cls,
        data: dict,
        *,
        default_half_life: int = DEFAULT_HALF_LIFE,
        default_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        grace_ticks: int = 0,
    ) -> MemoryEngine:
        """Restore from serialized state."""
        runtime = EntropyRuntime.from_dict(data, grace_ticks=grace_ticks)
        return cls(
            runtime,
            default_half_life=default_half_life,
            default_threshold=default_threshold,
        )

    # -- Internal helpers --

    def _put(self, mem: Memory) -> None:
        """Write a Memory into the TTLStore with the correct TTL."""
        self._runtime.store.set(
            _store_key(mem.key),
            mem.to_dict(),
            ttl_ticks=mem.ttl(),
            now=mem.last_accessed_at,
        )

    def _get(self, key: str) -> Memory | None:
        """Read a Memory from the TTLStore, or None if missing/expired."""
        try:
            data = self._runtime.store.get(_store_key(key))
        except (ExpiredStateError, KeyError):
            return None
        if not data:
            return None
        return Memory.from_dict(data)
