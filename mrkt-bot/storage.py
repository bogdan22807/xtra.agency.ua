from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BotState:
    mrkt_token: str = ""
    enabled: bool = False
    discount_percent: float = 15.0
    max_price_ton: float = 0.0
    poll_interval: float = 3.0
    collections: list[str] = field(default_factory=list)
    seen_ids: list[str] = field(default_factory=list)
    alerts_sent: int = 0

    def mark_seen(self, gift_id: str, limit: int = 5000) -> bool:
        """Return True if this id is new."""
        if gift_id in self.seen_ids:
            return False
        self.seen_ids.append(gift_id)
        if len(self.seen_ids) > limit:
            self.seen_ids = self.seen_ids[-limit:]
        return True


class StateStore:
    def __init__(self, path: Path, defaults: dict[str, Any] | None = None):
        self.path = path
        self.defaults = defaults or {}
        self.state = self._load()

    def _load(self) -> BotState:
        if not self.path.exists():
            state = BotState(**{k: v for k, v in self.defaults.items() if k in BotState.__dataclass_fields__})
            self._write(state)
            return state
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        known = {k: raw[k] for k in BotState.__dataclass_fields__ if k in raw}
        for key, value in self.defaults.items():
            known.setdefault(key, value)
        return BotState(**known)

    def _write(self, state: BotState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(asdict(state), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def save(self) -> None:
        self._write(self.state)