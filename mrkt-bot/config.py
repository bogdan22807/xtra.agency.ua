from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
STATE_PATH = DATA_DIR / "state.json"


@dataclass
class Settings:
    bot_token: str
    owner_id: int
    mrkt_token: str
    discount_percent: float
    max_price_ton: float
    poll_interval: float


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    owner_raw = os.getenv("OWNER_ID", "0").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is missing in .env")
    if not owner_raw.isdigit():
        raise RuntimeError("OWNER_ID must be a numeric Telegram user id")

    return Settings(
        bot_token=bot_token,
        owner_id=int(owner_raw),
        mrkt_token=os.getenv("MRKT_TOKEN", "").strip(),
        discount_percent=float(os.getenv("DISCOUNT_PERCENT", "15")),
        max_price_ton=float(os.getenv("MAX_PRICE_TON", "0")),
        poll_interval=float(os.getenv("POLL_INTERVAL", "3")),
    )