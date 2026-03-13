"""Memory dataclass and confidence decay model.

Confidence follows exponential decay: confidence = 2^(-elapsed / half_life).
A memory expires (TTL in the store) when confidence would drop below the threshold.
Accessing a memory resets its decay clock — things you use survive.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


# Default confidence threshold below which a memory is considered expired.
DEFAULT_CONFIDENCE_THRESHOLD = 0.1

# Default half-life in ticks.
DEFAULT_HALF_LIFE = 10


def ttl_from_half_life(half_life: int, threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> int:
    """Calculate the TTL (in ticks) for a given half-life and confidence threshold.

    Solves: threshold = 2^(-ttl / half_life)  =>  ttl = -half_life * log2(threshold)
    """
    if threshold <= 0.0 or threshold >= 1.0:
        msg = f"threshold must be in (0, 1), got {threshold}"
        raise ValueError(msg)
    if half_life < 1:
        msg = f"half_life must be >= 1, got {half_life}"
        raise ValueError(msg)
    return math.ceil(-half_life * math.log2(threshold))


def confidence_at(elapsed: int, half_life: int) -> float:
    """Compute confidence score after `elapsed` ticks since last access."""
    if elapsed < 0:
        return 1.0
    return 2.0 ** (-elapsed / half_life)


@dataclass(frozen=True, slots=True)
class Memory:
    """A single memory with decay metadata.

    Stored as the value inside entropy-os TTLStore. The TTL in the store
    is derived from half_life + threshold so the store handles expiry
    automatically. Confidence is computed on read from elapsed ticks.
    """

    key: str
    content: str
    half_life: int = DEFAULT_HALF_LIFE
    created_at: int = 0
    last_accessed_at: int = 0
    access_count: int = 0
    tags: tuple[str, ...] = ()
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD

    def confidence(self, now: int) -> float:
        """Current confidence score given the current tick."""
        elapsed = now - self.last_accessed_at
        return confidence_at(elapsed, self.half_life)

    def ttl(self) -> int:
        """TTL in ticks derived from half-life and threshold."""
        return ttl_from_half_life(self.half_life, self.threshold)

    def is_fading(self, now: int, warn_threshold: float = 0.5) -> bool:
        """True if confidence has dropped below the warning level."""
        return self.confidence(now) < warn_threshold

    def touched(self, now: int) -> Memory:
        """Return a new Memory with refreshed access time and incremented count."""
        return Memory(
            key=self.key,
            content=self.content,
            half_life=self.half_life,
            created_at=self.created_at,
            last_accessed_at=now,
            access_count=self.access_count + 1,
            tags=self.tags,
            threshold=self.threshold,
        )

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict for storage in TTLStore."""
        return {
            "key": self.key,
            "content": self.content,
            "half_life": self.half_life,
            "created_at": self.created_at,
            "last_accessed_at": self.last_accessed_at,
            "access_count": self.access_count,
            "tags": list(self.tags),
            "threshold": self.threshold,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Memory:
        """Deserialize from a dict (as stored in TTLStore)."""
        return cls(
            key=data["key"],
            content=data["content"],
            half_life=data["half_life"],
            created_at=data["created_at"],
            last_accessed_at=data["last_accessed_at"],
            access_count=data["access_count"],
            tags=tuple(data.get("tags", ())),
            threshold=data.get("threshold", DEFAULT_CONFIDENCE_THRESHOLD),
        )
