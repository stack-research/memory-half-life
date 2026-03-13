"""Tests for the Memory dataclass and decay math."""

import math

import pytest

from memoryhalflife.memory import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_HALF_LIFE,
    Memory,
    confidence_at,
    ttl_from_half_life,
)


class TestConfidenceAt:
    def test_zero_elapsed(self):
        assert confidence_at(0, half_life=10) == 1.0

    def test_one_half_life(self):
        assert confidence_at(10, half_life=10) == pytest.approx(0.5)

    def test_two_half_lives(self):
        assert confidence_at(20, half_life=10) == pytest.approx(0.25)

    def test_negative_elapsed_clamps(self):
        assert confidence_at(-5, half_life=10) == 1.0

    def test_large_elapsed_approaches_zero(self):
        assert confidence_at(100, half_life=10) < 0.001


class TestTTLFromHalfLife:
    def test_default_threshold(self):
        ttl = ttl_from_half_life(10)
        # threshold=0.1 => ttl = ceil(-10 * log2(0.1)) = ceil(33.22) = 34
        assert ttl == math.ceil(-10 * math.log2(DEFAULT_CONFIDENCE_THRESHOLD))

    def test_half_threshold(self):
        # threshold=0.5 => exactly 1 half-life
        assert ttl_from_half_life(10, threshold=0.5) == 10

    def test_invalid_threshold(self):
        with pytest.raises(ValueError):
            ttl_from_half_life(10, threshold=0.0)
        with pytest.raises(ValueError):
            ttl_from_half_life(10, threshold=1.0)

    def test_invalid_half_life(self):
        with pytest.raises(ValueError):
            ttl_from_half_life(0)


class TestMemory:
    def test_defaults(self):
        m = Memory(key="fact", content="the sky is blue")
        assert m.half_life == DEFAULT_HALF_LIFE
        assert m.threshold == DEFAULT_CONFIDENCE_THRESHOLD
        assert m.access_count == 0

    def test_confidence_at_creation(self):
        m = Memory(key="x", content="y", created_at=0, last_accessed_at=0)
        assert m.confidence(now=0) == 1.0

    def test_confidence_decays(self):
        m = Memory(key="x", content="y", half_life=10, last_accessed_at=0)
        assert m.confidence(now=10) == pytest.approx(0.5)
        assert m.confidence(now=20) == pytest.approx(0.25)

    def test_touched_resets_access(self):
        m = Memory(key="x", content="y", last_accessed_at=0, access_count=2)
        t = m.touched(now=5)
        assert t.last_accessed_at == 5
        assert t.access_count == 3
        assert t.confidence(now=5) == 1.0
        # Original unchanged (frozen)
        assert m.last_accessed_at == 0

    def test_is_fading(self):
        m = Memory(key="x", content="y", half_life=10, last_accessed_at=0)
        assert not m.is_fading(now=0)
        assert not m.is_fading(now=10)  # confidence=0.5, warn=0.5 => not fading (not < 0.5)
        assert m.is_fading(now=11)  # just past one half-life => fading

    def test_round_trip(self):
        m = Memory(
            key="fact/1",
            content="hello",
            half_life=5,
            created_at=2,
            last_accessed_at=3,
            access_count=1,
            tags=("a", "b"),
            threshold=0.2,
        )
        d = m.to_dict()
        m2 = Memory.from_dict(d)
        assert m == m2

    def test_tags_serialized_as_list(self):
        m = Memory(key="x", content="y", tags=("a", "b"))
        d = m.to_dict()
        assert d["tags"] == ["a", "b"]
