"""Tests for velocity check (Sprint 3 P2 #6)."""

import pytest

from app.security.velocity_check import VelocityChecker, MAX_REPEATS, _hash, _normalize


class _MockRedis:
    def __init__(self):
        self.store = {}
        self.expiries = {}

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key, ttl):
        self.expiries[key] = ttl


def test_normalize_collapses_whitespace_and_lowercases():
    assert _normalize("Hola, ¿qué tal?") == _normalize("HOLA  ¿qué   tal?")


def test_hash_stable_across_punctuation_only_diffs():
    assert _hash("Cuánto IRPF pago?") == _hash("Cuánto IRPF pago.")


def test_first_call_allowed():
    v = VelocityChecker(redis=_MockRedis())
    r = v.check("u1", "Cuánto IRPF pago?")
    assert r.allowed
    assert r.repeat_count == 1


def test_under_threshold_allowed():
    redis = _MockRedis()
    v = VelocityChecker(redis=redis)
    for _ in range(MAX_REPEATS):
        r = v.check("u1", "same question")
    assert r.allowed
    assert r.repeat_count == MAX_REPEATS


def test_over_threshold_blocked():
    redis = _MockRedis()
    v = VelocityChecker(redis=redis)
    for _ in range(MAX_REPEATS + 1):
        r = v.check("u1", "spam prompt")
    assert not r.allowed
    assert r.repeat_count == MAX_REPEATS + 1
    assert "varias veces" in r.reason.lower()


def test_different_users_isolated():
    redis = _MockRedis()
    v = VelocityChecker(redis=redis)
    for _ in range(MAX_REPEATS + 1):
        v.check("u1", "spam")
    r2 = v.check("u2", "spam")
    assert r2.allowed
    assert r2.repeat_count == 1


def test_different_questions_isolated():
    redis = _MockRedis()
    v = VelocityChecker(redis=redis)
    for _ in range(MAX_REPEATS + 1):
        v.check("u1", "first question")
    r = v.check("u1", "completely different question")
    assert r.allowed
    assert r.repeat_count == 1


def test_no_redis_fail_open():
    v = VelocityChecker(redis=None)
    r = v.check("u1", "anything")
    assert r.allowed
    assert r.reason in ("redis_unavailable", None)


def test_empty_input_allowed():
    v = VelocityChecker(redis=_MockRedis())
    assert v.check("", "x").allowed
    assert v.check("u1", "").allowed
