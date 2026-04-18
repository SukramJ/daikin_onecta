"""Tests for the resilience building blocks in ``support/``."""

from __future__ import annotations

import asyncio

import pytest

from custom_components.daikin_onecta.exceptions import DaikinApiError
from custom_components.daikin_onecta.exceptions import DaikinAuthError
from custom_components.daikin_onecta.exceptions import DaikinRateLimitError
from custom_components.daikin_onecta.support import CircuitBreaker
from custom_components.daikin_onecta.support import CircuitBreakerOpenError
from custom_components.daikin_onecta.support import CircuitState
from custom_components.daikin_onecta.support import RateLimitThrottle
from custom_components.daikin_onecta.support import retry_with_backoff


class TestRetryWithBackoff:
    """Phase 6.6 — retry behavior."""

    async def test_success_first_try(self):
        calls = 0

        @retry_with_backoff(tries=3, base_delay=0)
        async def f():
            nonlocal calls
            calls += 1
            return "ok"

        assert await f() == "ok"
        assert calls == 1

    async def test_retries_then_succeeds(self, monkeypatch):
        monkeypatch.setattr(asyncio, "sleep", _no_sleep)
        calls = 0

        @retry_with_backoff(tries=3, base_delay=0.01)
        async def f():
            nonlocal calls
            calls += 1
            if calls < 3:
                raise DaikinApiError("nope")
            return "ok"

        assert await f() == "ok"
        assert calls == 3

    async def test_exhausts_tries_then_raises(self, monkeypatch):
        monkeypatch.setattr(asyncio, "sleep", _no_sleep)
        calls = 0

        @retry_with_backoff(tries=2, base_delay=0.01)
        async def f():
            nonlocal calls
            calls += 1
            raise DaikinApiError("boom")

        with pytest.raises(DaikinApiError, match="boom"):
            await f()
        assert calls == 2

    async def test_auth_error_never_retried(self):
        calls = 0

        @retry_with_backoff(tries=3, base_delay=0)
        async def f():
            nonlocal calls
            calls += 1
            raise DaikinAuthError("expired")

        with pytest.raises(DaikinAuthError):
            await f()
        assert calls == 1

    async def test_rate_limit_error_never_retried(self):
        calls = 0

        @retry_with_backoff(tries=3, base_delay=0)
        async def f():
            nonlocal calls
            calls += 1
            raise DaikinRateLimitError("slow down", retry_after=30)

        with pytest.raises(DaikinRateLimitError):
            await f()
        assert calls == 1

    def test_invalid_tries_raises(self):
        with pytest.raises(ValueError):
            retry_with_backoff(tries=0)

    def test_invalid_delay_raises(self):
        with pytest.raises(ValueError):
            retry_with_backoff(base_delay=-1)


class TestCircuitBreaker:
    """Phase 6.7 — circuit breaker state transitions."""

    async def test_starts_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        assert cb.state is CircuitState.CLOSED
        await cb.before_call()  # must not raise

    async def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        await cb.record_failure()
        assert cb.state is CircuitState.CLOSED
        await cb.record_failure()
        assert cb.state is CircuitState.OPEN

    async def test_open_blocks_calls(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10)
        await cb.record_failure()
        with pytest.raises(CircuitBreakerOpenError):
            await cb.before_call()

    async def test_recovery_timeout_promotes_to_half_open(self, monkeypatch):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        await cb.record_failure()
        assert cb.state is CircuitState.OPEN
        # Fast-forward time artificially
        import time as time_mod

        original = time_mod.monotonic
        monkeypatch.setattr(
            "custom_components.daikin_onecta.support.circuit_breaker.time.monotonic",
            lambda: original() + 1.0,
        )
        await cb.before_call()
        assert cb.state is CircuitState.HALF_OPEN

    async def test_half_open_success_closes(self, monkeypatch):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        await cb.record_failure()
        import time as time_mod

        original = time_mod.monotonic
        monkeypatch.setattr(
            "custom_components.daikin_onecta.support.circuit_breaker.time.monotonic",
            lambda: original() + 1.0,
        )
        await cb.before_call()  # → HALF_OPEN
        await cb.record_success()
        assert cb.state is CircuitState.CLOSED

    async def test_half_open_failure_reopens(self, monkeypatch):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        await cb.record_failure()
        import time as time_mod

        original = time_mod.monotonic
        monkeypatch.setattr(
            "custom_components.daikin_onecta.support.circuit_breaker.time.monotonic",
            lambda: original() + 1.0,
        )
        await cb.before_call()  # → HALF_OPEN
        await cb.record_failure()
        assert cb.state is CircuitState.OPEN

    async def test_success_resets_failure_counter(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        await cb.record_failure()
        await cb.record_failure()
        await cb.record_success()
        await cb.record_failure()
        await cb.record_failure()
        # Counter was reset, so still CLOSED
        assert cb.state is CircuitState.CLOSED

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError):
            CircuitBreaker(failure_threshold=0)

    def test_invalid_timeout_raises(self):
        with pytest.raises(ValueError):
            CircuitBreaker(failure_threshold=1, recovery_timeout=0)


class TestRateLimitThrottle:
    """Throttle calculations based on rate-limit telemetry."""

    def _limits(self, **overrides):
        base = {
            "minute": 200,
            "day": 20000,
            "remaining_minutes": 200,
            "remaining_day": 20000,
            "retry_after": 0,
            "ratelimit_reset": 60,
        }
        base.update(overrides)
        return base

    def test_no_delay_when_quota_healthy(self):
        t = RateLimitThrottle()
        assert t.recommended_delay(self._limits()) == 0.0

    def test_delay_when_minute_low(self):
        t = RateLimitThrottle(min_remaining_pct=0.1, safety_margin=2)
        delay = t.recommended_delay(self._limits(remaining_minutes=10, ratelimit_reset=30))
        assert delay == 32.0  # 30 + safety_margin

    def test_uses_retry_after_when_day_exhausted(self):
        t = RateLimitThrottle(safety_margin=5)
        delay = t.recommended_delay(self._limits(remaining_day=0, retry_after=3000))
        assert delay == 3005.0

    def test_invalid_safety_margin_raises(self):
        with pytest.raises(ValueError):
            RateLimitThrottle(safety_margin=-1)

    def test_invalid_min_remaining_pct_raises(self):
        with pytest.raises(ValueError):
            RateLimitThrottle(min_remaining_pct=0)
        with pytest.raises(ValueError):
            RateLimitThrottle(min_remaining_pct=1)


async def _no_sleep(*_args, **_kwargs):
    """Drop-in replacement for asyncio.sleep used in retry tests."""
    return None
