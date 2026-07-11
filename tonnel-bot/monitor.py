from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from storage import StateStore
from tonnel_client import GiftDeal, TonnelClient

logger = logging.getLogger(__name__)

AlertCallback = Callable[[GiftDeal], Awaitable[None]]


def is_lol_price(
    deal: GiftDeal,
    discount_percent: float,
    max_price_ton: float,
) -> bool:
    by_floor = False
    if deal.floor_ton and deal.floor_ton > 0 and discount_percent > 0:
        threshold = deal.floor_ton * (1 - discount_percent / 100)
        by_floor = deal.price_ton <= threshold + 1e-12

    by_cap = max_price_ton > 0 and deal.price_ton <= max_price_ton + 1e-12
    return by_floor or by_cap


def matches_collections(deal: GiftDeal, collections: list[str]) -> bool:
    if not collections:
        return True
    name = (deal.collection or "").strip().lower()
    wanted = {c.strip().lower() for c in collections if c.strip()}
    return name in wanted


class PriceMonitor:
    def __init__(
        self,
        client: TonnelClient,
        store: StateStore,
        on_alert: AlertCallback,
    ):
        self.client = client
        self.store = store
        self.on_alert = on_alert
        self._primed = False
        self.last_error: str | None = None
        self.last_scan_count = 0

    def _attach_floor(self, deal: GiftDeal) -> GiftDeal:
        key = (deal.collection or "").strip().lower()
        floor = self.store.state.floors.get(key)
        if floor is None:
            return deal
        discount = (1 - deal.price_ton / floor) * 100 if floor > 0 else None
        return GiftDeal(
            id=deal.id,
            title=deal.title,
            collection=deal.collection,
            model=deal.model,
            backdrop=deal.backdrop,
            symbol=deal.symbol,
            number=deal.number,
            price_ton=deal.price_ton,
            floor_ton=floor,
            discount_pct=discount,
            link=deal.link,
            raw=deal.raw,
        )

    def _fetch_batch(self) -> list[GiftDeal]:
        state = self.store.state
        if state.tonnel_auth:
            self.client.set_auth(state.tonnel_auth)

        deals: list[GiftDeal] = []
        collections = state.collections

        if collections:
            for name in collections:
                floor = self.client.collection_floor(name)
                if floor is not None:
                    key = name.strip().lower()
                    prev = state.floors.get(key)
                    state.floors[key] = floor if prev is None else min(prev, floor)
                deals.extend(self.client.search(gift_name=name, newest=False, limit=10))
                deals.extend(self.client.search(gift_name=name, newest=True, limit=15))
        else:
            newest = self.client.search(newest=True, limit=30)
            cheapest = self.client.search(newest=False, limit=30)
            deals.extend(newest)
            deals.extend(cheapest)
            by_name: dict[str, float] = {}
            for deal in cheapest:
                key = deal.collection.strip().lower()
                if not key:
                    continue
                by_name[key] = min(by_name.get(key, deal.price_ton), deal.price_ton)
            for key, floor in by_name.items():
                prev = state.floors.get(key)
                state.floors[key] = floor if prev is None else min(prev, floor)

        unique: dict[str, GiftDeal] = {}
        for deal in deals:
            unique.setdefault(deal.id, self._attach_floor(deal))
        return list(unique.values())

    async def scan_once(self) -> int:
        state = self.store.state
        try:
            unique = await asyncio.to_thread(self._fetch_batch)
        except Exception as exc:
            self.last_error = str(exc)
            raise

        self.last_scan_count = len(unique)
        self.last_error = None

        if not self._primed:
            for deal in unique:
                state.mark_seen(deal.id)
            self._primed = True
            self.store.save()
            logger.info("Monitor primed with %s gifts", len(unique))
            return 0

        alerts = 0
        for deal in unique:
            if not matches_collections(deal, state.collections):
                continue
            if not is_lol_price(deal, state.discount_percent, state.max_price_ton):
                continue
            if not state.mark_seen(deal.id):
                continue
            await self.on_alert(deal)
            state.alerts_sent += 1
            alerts += 1

        self.store.save()
        return alerts