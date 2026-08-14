from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PersistentStore:
    def __init__(self, path: str = "data/last_dashboard.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, payload: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(payload), encoding="utf-8")

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
