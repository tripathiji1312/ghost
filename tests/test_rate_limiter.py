import time

from ghost.rate_limiter import RateLimiter


class TestRateLimiter:
    def test_set_interval(self):
        RateLimiter.set_interval(0.01)
        assert RateLimiter.MIN_INTERVAL == 0.01

    def test_wait_allows_call_when_ready(self):
        RateLimiter.set_interval(0.01)
        start = time.time()
        RateLimiter.wait()
        elapsed = time.time() - start
        assert elapsed < 0.5

    def test_wait_blocks_when_called_too_soon(self):
        RateLimiter.set_interval(0.2)
        RateLimiter.wait()
        start = time.time()
        RateLimiter.wait()
        elapsed = time.time() - start
        assert elapsed >= 0.15

    def test_wait_consecutive_with_low_interval(self):
        RateLimiter.set_interval(0.01)
        RateLimiter.wait()
        RateLimiter.wait()
        RateLimiter.wait()
        assert RateLimiter._last_call > 0
