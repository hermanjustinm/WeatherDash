import time
import threading
from typing import Any, Optional

_store: dict[str, tuple[Any, float]] = {}
_lock = threading.Lock()


def get(key: str) -> Optional[Any]:
    with _lock:
        entry = _store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del _store[key]
            return None
        return value


def set(key: str, value: Any, ttl: int) -> None:
    with _lock:
        _store[key] = (value, time.time() + ttl)


def delete(key: str) -> None:
    with _lock:
        _store.pop(key, None)


def clear() -> None:
    with _lock:
        _store.clear()


def ttl_remaining(key: str) -> Optional[float]:
    with _lock:
        entry = _store.get(key)
        if entry is None:
            return None
        _, expires_at = entry
        remaining = expires_at - time.time()
        return max(0.0, remaining)
