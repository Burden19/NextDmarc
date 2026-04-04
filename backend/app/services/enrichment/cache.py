import asyncio
from dataclasses import dataclass
from time import monotonic


@dataclass(slots=True)
class _CacheEntry:
    expires_at: float
    value: dict[str, object]


class TtlCache:
    def __init__(self, *, ttl_seconds: int = 900) -> None:
        self._ttl_seconds = ttl_seconds
        self._items: dict[str, _CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> dict[str, object] | None:
        async with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            if monotonic() >= entry.expires_at:
                self._items.pop(key, None)
                return None
            return dict(entry.value)

    async def set(self, key: str, value: dict[str, object]) -> None:
        async with self._lock:
            self._items[key] = _CacheEntry(
                expires_at=monotonic() + max(1, self._ttl_seconds),
                value=dict(value),
            )
