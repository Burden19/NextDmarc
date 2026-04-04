import asyncio
from time import monotonic


class RateProtector:
    def __init__(self, *, requests_per_second: float) -> None:
        self._minimum_interval = 1.0 / max(0.01, requests_per_second)
        self._lock = asyncio.Lock()
        self._last_request_at = 0.0

    async def wait_turn(self) -> None:
        async with self._lock:
            now = monotonic()
            elapsed = now - self._last_request_at
            wait_seconds = self._minimum_interval - elapsed
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            self._last_request_at = monotonic()
