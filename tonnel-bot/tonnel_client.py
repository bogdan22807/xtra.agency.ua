from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from curl_cffi import requests

API_URL = "https://gifts2.tonnel.network/api/pageGifts"
FEE_MULT = 1.10  # buyer usually pays ~10% on top of listed raw price


@dataclass
class GiftDeal:
    id: str
    title: str
    collection: str
    model: str
    backdrop: str
    symbol: str
    number: int | None
    price_ton: float
    floor_ton: float | None
    discount_pct: float | None
    link: str
    raw: dict[str, Any]

    @property
    def display_name(self) -> str:
        base = self.title or self.collection or "Gift"
        if self.number is not None:
            return f"{base} #{self.number}"
        return base

    @property
    def buyer_price_ton(self) -> float:
        return self.price_ton * FEE_MULT


def _strip_rarity(value: str) -> str:
    return re.sub(r"\s*\([^)]*%\)\s*$", "", value or "").strip()


def parse_gift(raw: dict[str, Any], floor_ton: float | None = None) -> GiftDeal | None:
    gift_id = raw.get("gift_id")
    if gift_id is None:
        return None
    try:
        price = float(raw.get("price"))
    except (TypeError, ValueError):
        return None

    name = str(raw.get("name") or "")
    model = str(raw.get("model") or "")
    backdrop = str(raw.get("backdrop") or "")
    symbol = str(raw.get("symbol") or "")
    number = raw.get("gift_num")
    try:
        number_int = int(number) if number is not None else None
    except (TypeError, ValueError):
        number_int = None

    discount_pct = None
    if floor_ton and floor_ton > 0:
        discount_pct = (1 - price / floor_ton) * 100

    # Market deep-link + searchable fallback
    link = f"https://market.tonnel.network/?gift={gift_id}"

    return GiftDeal(
        id=str(gift_id),
        title=name,
        collection=name,
        model=_strip_rarity(model) or model,
        backdrop=_strip_rarity(backdrop) or backdrop,
        symbol=_strip_rarity(symbol) or symbol,
        number=number_int,
        price_ton=price,
        floor_ton=floor_ton,
        discount_pct=discount_pct,
        link=link,
        raw=raw,
    )


class TonnelClient:
    def __init__(self, auth: str = ""):
        self.auth = auth.strip()
        self._impersonates = ("safari15_5", "safari17_0", "firefox133")

    def set_auth(self, auth: str) -> None:
        self.auth = auth.strip()

    def _headers(self) -> dict[str, str]:
        return {
            "authority": "gifts2.tonnel.network",
            "accept": "*/*",
            "content-type": "application/json",
            "origin": "https://market.tonnel.network",
            "referer": "https://market.tonnel.network/",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
            ),
        }

    def _base_filter(self, gift_name: str | None = None) -> dict[str, Any]:
        data: dict[str, Any] = {
            "price": {"$exists": True},
            "refunded": {"$ne": True},
            "buyer": {"$exists": False},
            "export_at": {"$exists": True},
            "asset": "TON",
        }
        if gift_name:
            data["gift_name"] = gift_name
        return data

    def page_gifts(
        self,
        *,
        page: int = 1,
        limit: int = 30,
        sort: dict[str, int] | None = None,
        gift_name: str | None = None,
        price_range: list[float] | None = None,
    ) -> list[dict[str, Any]]:
        payload = {
            "page": page,
            "limit": min(limit, 30),
            "sort": json.dumps(sort or {"price": 1, "gift_id": -1}),
            "filter": json.dumps(self._base_filter(gift_name)),
            "price_range": price_range,
            "user_auth": self.auth or "",
        }
        last_error = "unknown"
        for impersonate in self._impersonates:
            resp = requests.post(
                API_URL,
                json=payload,
                headers=self._headers(),
                impersonate=impersonate,
                timeout=25,
            )
            if resp.status_code == 403:
                last_error = f"403 Cloudflare ({impersonate})"
                continue
            if resp.status_code >= 400:
                raise RuntimeError(f"Tonnel API {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            if isinstance(data, dict) and data.get("error"):
                raise RuntimeError(f"Tonnel API error: {data.get('error')}")
            if not isinstance(data, list):
                raise RuntimeError(f"Unexpected Tonnel response: {str(data)[:200]}")
            return data
        raise RuntimeError(f"Tonnel API blocked: {last_error}")

    def search(
        self,
        *,
        gift_name: str | None = None,
        newest: bool = False,
        limit: int = 30,
    ) -> list[GiftDeal]:
        sort = (
            {"message_post_time": -1, "gift_id": -1}
            if newest
            else {"price": 1, "gift_id": -1}
        )
        items = self.page_gifts(sort=sort, gift_name=gift_name, limit=limit)
        deals: list[GiftDeal] = []
        for item in items:
            deal = parse_gift(item)
            if deal:
                deals.append(deal)
        return deals

    def collection_floor(self, gift_name: str) -> float | None:
        items = self.page_gifts(
            sort={"price": 1, "gift_id": -1},
            gift_name=gift_name,
            limit=1,
        )
        if not items:
            return None
        try:
            return float(items[0]["price"])
        except (KeyError, TypeError, ValueError):
            return None

    def ping(self) -> bool:
        self.page_gifts(limit=1)
        return True