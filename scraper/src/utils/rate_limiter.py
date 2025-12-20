"""Rate limiter with randomized delays and exponential backoff."""

import asyncio
import random
import time
from typing import Dict, Optional


class RateLimiter:
    """Rate limiter that enforces delays between requests to the same domain."""

    def __init__(
        self,
        min_delay: float = 2.0,
        max_delay: float = 4.0,
        backoff_factor: float = 2.0,
        max_retries: int = 3
    ):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.max_retries = max_retries
        self._last_request_time: Dict[str, float] = {}
        self._failure_counts: Dict[str, int] = {}

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc

    def _get_delay(self, domain: str) -> float:
        """Calculate delay with exponential backoff for failures."""
        base_delay = random.uniform(self.min_delay, self.max_delay)
        failure_count = self._failure_counts.get(domain, 0)
        if failure_count > 0:
            backoff = self.backoff_factor ** failure_count
            base_delay *= backoff
        return min(base_delay, 60.0)  # Cap at 60 seconds

    def wait(self, url: str) -> None:
        """Synchronous wait before making a request."""
        domain = self._get_domain(url)
        delay = self._get_delay(domain)

        last_time = self._last_request_time.get(domain, 0)
        elapsed = time.time() - last_time

        if elapsed < delay:
            time.sleep(delay - elapsed)

        self._last_request_time[domain] = time.time()

    async def async_wait(self, url: str) -> None:
        """Async wait before making a request."""
        domain = self._get_domain(url)
        delay = self._get_delay(domain)

        last_time = self._last_request_time.get(domain, 0)
        elapsed = time.time() - last_time

        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)

        self._last_request_time[domain] = time.time()

    def record_success(self, url: str) -> None:
        """Record a successful request, resetting failure count."""
        domain = self._get_domain(url)
        self._failure_counts[domain] = 0

    def record_failure(self, url: str) -> bool:
        """
        Record a failed request. Returns True if retry is allowed.
        """
        domain = self._get_domain(url)
        self._failure_counts[domain] = self._failure_counts.get(domain, 0) + 1
        return self._failure_counts[domain] <= self.max_retries

    def get_failure_count(self, url: str) -> int:
        """Get current failure count for a domain."""
        domain = self._get_domain(url)
        return self._failure_counts.get(domain, 0)
