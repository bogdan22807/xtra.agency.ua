from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp

API_URL = "https://api.tgmrkt.io/api/v1"
NANO = 1_000_000_000


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


def _nano_to_ton(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value) / NANO
    except (TypeError, ValueError):
        return None


def parse_gift(raw: dict[str, Any]) -> GiftDeal | None:
    gift_id = str(raw.get("id") or raw.get("giftId") or "").strip()
    if not gift_id:
        return None

    price_ton = _nano_to_ton(raw.get("salePrice"))
    if price_ton is None:
        return None

    floor_ton = _nano_to_ton(
        raw.get("floorPriceNanoTONsByCollection")
        or raw.get("floorPriceNanoTONsByBackdropModel")
    )
    discount_pct = None
    if floor_ton and floor_ton > 0:
        discount_pct = (1 - price_ton / floor_ton) * 100

    collection = str(raw.get("collectionName") or raw.get("collectionTitle") or "")
    title = str(raw.get("title") or raw.get("name") or collection or "Gift")
    model = str(raw.get("modelName") or raw.get("modelTitle") or "")
    backdrop = str(raw.get("backdropName") or "")
    symbol = str(raw.get("symbolName") or "")
    number = raw.get("number")
    try:
        number_int = int(number) if number is not None else None
    except (TypeError, ValueError):
        number_int = None

    # Mini App deep-link into MRKT gift card
    link = f"https://t.me/mrkt/app?startapp={gift_id}"

    return GiftDeal(
        id=gift_id,
        title=title,
        collection=collection,
        model=model,
        backdrop=backdrop,
        symbol=symbol,
        number=number_int,
        price_ton=price_ton,
        floor_ton=floor_ton,
        discount_pct=discount_pct,
        link=link,
        raw=raw,
    )


class MrktClient:
    def __init__(self, token: str):
        self.token = token.strip()
        self._session: aiohttp.ClientSession | None = None

    def set_token(self, token: str) -> None:
        self.token = token.strip()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=20),
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self.token,
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://cdn.tgmrkt.io",
            "Referer": "https://cdn.tgmrkt.io/",
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.6367.82 Mobile Safari/537.36"
            ),
            "Cookie": f"access_token={self.token}",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        if not self.token:
            raise RuntimeError("MRKT token is empty. Use /token <uuid>")

        session = await self._get_session()
        url = f"{API_URL}{endpoint}"
        async with session.request(
            method,
            url,
            headers=self._headers(),
            json=json_body,
        ) as resp:
            text = await resp.text()
            if resp.status == 401:
                raise RuntimeError("MRKT token invalid/expired. Update via /token")
            if resp.status >= 400:
                raise RuntimeError(f"MRKT API {resp.status}: {text[:300]}")
            if not text:
                return {}
            return await resp.json(content_type=None)

    async def search_gifts(
        self,
        collection_names: list[str] | None = None,
        ordering: str | None = "Price",
        low_to_high: bool = True,
        count: int = 20,
        cursor: str = "",
        max_price_nano: int | None = None,
    ) -> list[GiftDeal]:
        payload = {
            "collectionNames": collection_names or [],
            "modelNames": [],
            "backdropNames": [],
            "symbolNames": [],
            "ordering": ordering,
            "lowToHigh": low_to_high,
            "maxPrice": max_price_nano,
            "minPrice": None,
            "mintable": None,
            "number": None,
            "count": min(count, 20),
            "cursor": cursor,
            "query": None,
            "promotedFirst": False,
        }
        data = await self._request("POST", "/gifts/saling", payload)
        gifts = data.get("gifts") or []
        parsed: list[GiftDeal] = []
        for item in gifts:
            deal = parse_gift(item)
            if deal:
                parsed.append(deal)
        return parsed

    async def get_feed_listings(self) -> list[GiftDeal]:
        data = await self._request("POST", "/feed", {})
        items = data.get("items") or data.get("feed") or []
        deals: list[GiftDeal] = []
        for item in items:
            event_type = str(item.get("type") or "").lower()
            if event_type and event_type not in {"listing", "change_price", "price_change"}:
                # still try if gift payload exists
                pass
            gift_raw = item.get("gift") or item
            if not isinstance(gift_raw, dict):
                continue
            # Prefer amount from feed event when present
            if item.get("amount") and not gift_raw.get("salePrice"):
                gift_raw = {**gift_raw, "salePrice": item["amount"]}
            deal = parse_gift(gift_raw)
            if deal:
                deals.append(deal)
        return deals

    async def ping(self) -> bool:
        await self.search_gifts(count=1)
        return True