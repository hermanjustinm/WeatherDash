from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class CachedResult:
    data: Any
    fetched_at: float


class TTLCacheStore:
    def __init__(self) -> None:
        self._store: dict[str, CachedResult] = {}

    def get_or_set(self, key: str, ttl_seconds: int, loader: Callable[[], Any]) -> CachedResult:
        now = time.time()
        cached = self._store.get(key)
        if cached and (now - cached.fetched_at) < ttl_seconds:
            return cached

        data = loader()
        wrapped = CachedResult(data=data, fetched_at=now)
        self._store[key] = wrapped
        return wrapped
