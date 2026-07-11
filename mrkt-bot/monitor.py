from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from mrkt_client import GiftDeal, MrktClient
from storage import StateStore

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
    title = (deal.title or "").strip().lower()
    wanted = {c.strip().lower() for c in collections if c.strip()}
    return name in wanted or title in wanted


class PriceMonitor:
    def __init__(
        self,
        client: MrktClient,
        store: StateStore,
        on_alert: AlertCallback,
    ):
        self.client = client
        self.store = store
        self.on_alert = on_alert
        self._primed = False
        self.last_error: str | None = None
        self.last_scan_count = 0

    async def scan_once(self) -> int:
        state = self.store.state
        if not state.mrkt_token:
            raise RuntimeError("MRKT token is not set")

        self.client.set_token(state.mrkt_token)
        deals: list[GiftDeal] = []

        try:
            feed = await self.client.get_feed_listings()
            deals.extend(feed)
        except Exception as exc:
            logger.warning("Feed scan failed: %s", exc)

        # Also pull cheapest listings for watched collections (or global sample)
        collections = state.collections or [None]
        for collection in collections:
            names = [collection] if collection else []
            try:
                page = await self.client.search_gifts(
                    collection_names=names,
                    ordering="Price",
                    low_to_high=True,
                    count=20,
                )
                deals.extend(page)
            except Exception as exc:
                logger.warning("Saling scan failed for %s: %s", collection, exc)
                self.last_error = str(exc)
                raise

        # Newest listings help catch fresh undercuts
        try:
            newest = await self.client.search_gifts(
                collection_names=state.collections or [],
                ordering=None,
                low_to_high=False,
                count=20,
            )
            deals.extend(newest)
        except Exception as exc:
            logger.debug("Newest scan skipped: %s", exc)

        # Dedup by id keeping first
        unique: dict[str, GiftDeal] = {}
        for deal in deals:
            unique.setdefault(deal.id, deal)

        self.last_scan_count = len(unique)
        self.last_error = None
        alerts = 0

        # First successful scan only seeds seen ids to avoid spam flood
        if not self._primed:
            for deal in unique.values():
                state.mark_seen(deal.id)
            self._primed = True
            self.store.save()
            logger.info("Monitor primed with %s gifts", len(unique))
            return 0

        for deal in unique.values():
            if not matches_collections(deal, state.collections):
                continue
            if not is_lol_price(deal, state.discount_percent, state.max_price_ton):
                continue
            if not state.mark_seen(deal.id):
                continue
            await self.on_alert(deal)
            state.alerts_sent += 1
            alerts += 1

        if alerts:
            self.store.save()
        else:
            # persist seen growth periodically
            self.store.save()
        return alerts