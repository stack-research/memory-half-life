"""Tests for the MemoryEngine."""

from memoryhalflife.engine import MemoryEngine


class TestStoreAndRecall:
    def test_store_returns_memory(self):
        eng = MemoryEngine()
        mem = eng.store("sky", "the sky is blue")
        assert mem.key == "sky"
        assert mem.content == "the sky is blue"
        assert mem.confidence(eng.now) == 1.0

    def test_recall_returns_memory(self):
        eng = MemoryEngine()
        eng.store("sky", "the sky is blue")
        mem = eng.recall("sky")
        assert mem is not None
        assert mem.content == "the sky is blue"

    def test_recall_missing_returns_none(self):
        eng = MemoryEngine()
        assert eng.recall("nope") is None

    def test_recall_refreshes_memory(self):
        eng = MemoryEngine(default_half_life=10)
        eng.store("fact", "water is wet")
        eng.tick(5)
        mem = eng.recall("fact")
        assert mem is not None
        # After recall, last_accessed_at should be current tick (5)
        assert mem.last_accessed_at == 5
        assert mem.access_count == 1
        # Confidence should be 1.0 since we just touched it
        assert mem.confidence(eng.now) == 1.0

    def test_peek_does_not_refresh(self):
        eng = MemoryEngine(default_half_life=10)
        eng.store("fact", "water is wet")
        eng.tick(5)
        mem = eng.peek("fact")
        assert mem is not None
        assert mem.last_accessed_at == 0  # not refreshed
        assert mem.access_count == 0


class TestDecay:
    def test_memory_expires_after_ttl(self):
        eng = MemoryEngine(default_half_life=5, default_threshold=0.5)
        # With half_life=5, threshold=0.5 => TTL=5 ticks
        eng.store("temp", "fleeting thought")
        eng.tick(5)
        # Should be expired now
        assert eng.peek("temp") is None

    def test_recall_keeps_memory_alive(self):
        eng = MemoryEngine(default_half_life=5, default_threshold=0.5)
        eng.store("fact", "important")
        eng.tick(3)
        eng.recall("fact")  # refresh at tick 3
        eng.tick(3)  # now at tick 6 — but memory was refreshed at 3, so TTL expires at 8
        mem = eng.peek("fact")
        assert mem is not None

    def test_unreinforced_memory_dies(self):
        eng = MemoryEngine(default_half_life=5, default_threshold=0.5)
        eng.store("a", "reinforced")
        eng.store("b", "ignored")
        eng.tick(3)
        eng.recall("a")  # reinforce a
        eng.tick(3)
        assert eng.peek("a") is not None
        assert eng.peek("b") is None  # b expired


class TestForget:
    def test_forget_existing(self):
        eng = MemoryEngine()
        eng.store("x", "value")
        assert eng.forget("x") is True
        assert eng.recall("x") is None

    def test_forget_missing(self):
        eng = MemoryEngine()
        assert eng.forget("nope") is False


class TestMemories:
    def test_lists_all_living(self):
        eng = MemoryEngine()
        eng.store("a", "alpha")
        eng.store("b", "beta")
        mems = eng.memories()
        assert len(mems) == 2
        assert mems[0].key == "a"
        assert mems[1].key == "b"

    def test_excludes_expired(self):
        eng = MemoryEngine(default_half_life=3, default_threshold=0.5)
        eng.store("short", "gone soon")
        eng.store("long", "sticks around", half_life=100)
        eng.tick(3)
        mems = eng.memories()
        assert len(mems) == 1
        assert mems[0].key == "long"


class TestFading:
    def test_identifies_fading_memories(self):
        eng = MemoryEngine(default_half_life=10)
        eng.store("old", "getting stale")
        eng.store("new", "just stored")
        eng.tick(10)
        eng.store("new", "refreshed")  # re-store new at tick 10
        fading = eng.fading(warn_threshold=0.6)
        assert len(fading) == 1
        assert fading[0].key == "old"


class TestSerialization:
    def test_round_trip(self):
        eng = MemoryEngine(default_half_life=8)
        eng.store("fact", "round trip test", tags=("test",))
        eng.tick(2)
        state = eng.to_dict()

        eng2 = MemoryEngine.from_dict(state, default_half_life=8)
        mem = eng2.peek("fact")
        assert mem is not None
        assert mem.content == "round trip test"
        assert mem.tags == ("test",)


class TestTags:
    def test_store_with_tags(self):
        eng = MemoryEngine()
        mem = eng.store("x", "tagged", tags=("a", "b"))
        assert mem.tags == ("a", "b")
        recalled = eng.recall("x")
        assert recalled.tags == ("a", "b")
