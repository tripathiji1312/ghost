"""
Rate limiting utilities for API calls.

Provides:
1. RateLimiter - Global traffic cop to prevent exceeding API rate limits
2. call_with_retry - Decorator for exponential backoff on rate limit errors
"""

import time
import random
from threading import Lock
from functools import wraps
from console import Console, countdown, Colors, Icons


class RateLimiter:
    """
    Global rate limiter to ensure API calls don't exceed rate limits.
    
    For Groq Free Tier (~30 RPM), use MIN_INTERVAL = 6-10 seconds to be safe.
    The free tier is very strict and 2 seconds is not enough.
    """
    _last_call = 0
    _lock = Lock()
    
    # Minimum seconds between API calls
    # Groq Free Tier is VERY strict - use 10 seconds to be safe
    MIN_INTERVAL = 10.0

    @classmethod
    def wait(cls):
        """
        Blocks if called too soon after the last API call.
        Call this before every API request.
        """
        with cls._lock:
            current_time = time.time()
            elapsed = current_time - cls._last_call
            
            if elapsed < cls.MIN_INTERVAL:
                sleep_duration = cls.MIN_INTERVAL - elapsed
                countdown(sleep_duration, "API cooldown")
            
            cls._last_call = time.time()

    @classmethod
    def set_interval(cls, seconds: float):
        """Adjust the minimum interval between API calls."""
        cls.MIN_INTERVAL = seconds
        Console.info(f"Rate limiter interval set to {seconds}s")


def call_with_retry(max_retries: int = 5, base_delay: float = 2.0):
    """
    Decorator that retries the function on rate limit errors with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 5)
        base_delay: Initial delay in seconds, doubles each retry (default: 2.0)
    
    Example:
        @call_with_retry(max_retries=5, base_delay=2.0)
        def call_api(prompt):
            return client.chat.completions.create(...)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    
                    # Check for rate limit indicators
                    is_rate_limit = any(indicator in error_msg for indicator in [
                        "429", 
                        "rate limit", 
                        "too many requests",
                        "rate_limit",
                        "ratelimit",
                        "quota exceeded",
                        "requests per minute"
                    ])
                    
                    if is_rate_limit:
                        if attempt == max_retries - 1:
                            Console.error(f"Rate limit: Max retries ({max_retries}) exceeded")
                            raise e
                        
                        # Exponential backoff + jitter (prevents thundering herd)
                        sleep_time = (base_delay * (2 ** attempt)) + random.uniform(0.1, 1.0)
                        Console.rate_limited(sleep_time, attempt + 1, max_retries)
                        countdown(sleep_time, "Retry cooldown")
                    else:
                        # Non-rate-limit error, fail immediately
                        raise e
            
            # Should not reach here, but just in case
            return func(*args, **kwargs)
        return wrapper
    return decorator
