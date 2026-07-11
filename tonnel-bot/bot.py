from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import STATE_PATH, load_settings
from monitor import PriceMonitor, is_lol_price
from storage import StateStore
from tonnel_client import GiftDeal, TonnelClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("tonnel-bot")

settings = load_settings()
store = StateStore(
    STATE_PATH,
    defaults={
        "discount_percent": settings.discount_percent,
        "max_price_ton": settings.max_price_ton,
        "poll_interval": settings.poll_interval,
        "enabled": False,
        "collections": [],
        "tonnel_auth": settings.tonnel_auth,
    },
)

bot = Bot(token=settings.bot_token)
dp = Dispatcher()
client = TonnelClient(store.state.tonnel_auth)
monitor: PriceMonitor | None = None
_monitor_task: asyncio.Task | None = None


def owner_only(message: Message) -> bool:
    return message.from_user is not None and message.from_user.id == settings.owner_id


def format_deal(deal: GiftDeal) -> str:
    lines = [
        "🔥 <b>TONNEL LOL PRICE</b>",
        f"<b>{deal.display_name}</b>",
    ]
    if deal.model:
        lines.append(f"Модель: {deal.model}")
    if deal.backdrop:
        lines.append(f"Фон: {deal.backdrop}")
    if deal.symbol:
        lines.append(f"Узор: {deal.symbol}")

    lines.append(f"Цена: <b>{deal.price_ton:.4f} TON</b>")
    lines.append(f"С комиссией ~{deal.buyer_price_ton:.4f} TON")
    if deal.floor_ton is not None:
        lines.append(f"Floor: {deal.floor_ton:.4f} TON")
    if deal.discount_pct is not None:
        lines.append(f"Скидка к floor: <b>{deal.discount_pct:.1f}%</b>")
    lines.append(f"ID: <code>{deal.id}</code>")
    lines.append(f'<a href="{deal.link}">Открыть Tonnel</a>')
    return "\n".join(lines)


async def send_alert(deal: GiftDeal) -> None:
    await bot.send_message(
        settings.owner_id,
        format_deal(deal),
        parse_mode="HTML",
        disable_web_page_preview=False,
    )


async def monitor_loop() -> None:
    assert monitor is not None
    while True:
        state = store.state
        if not state.enabled:
            await asyncio.sleep(1)
            continue
        try:
            alerts = await monitor.scan_once()
            if alerts:
                logger.info("Sent %s alerts", alerts)
        except Exception as exc:
            logger.exception("Scan error: %s", exc)
            monitor.last_error = str(exc)
            await asyncio.sleep(max(5.0, state.poll_interval))
            continue
        await asyncio.sleep(max(1.0, state.poll_interval))


def ensure_monitor() -> PriceMonitor:
    global monitor, _monitor_task
    if monitor is None:
        monitor = PriceMonitor(client, store, send_alert)
    if _monitor_task is None or _monitor_task.done():
        _monitor_task = asyncio.create_task(monitor_loop(), name="tonnel-monitor")
    return monitor


@dp.message(Command("start", "help"))
async def cmd_start(message: Message) -> None:
    if not owner_only(message):
        await message.answer("Доступ только владельцу.")
        return
    ensure_monitor()
    await message.answer(
        "Tonnel sniper bot\n\n"
        "Команды:\n"
        "/on — включить мониторинг\n"
        "/off — выключить\n"
        "/status — статус\n"
        "/discount 15 — % ниже floor\n"
        "/maxprice 5 — потолок цены в TON (0 = выкл)\n"
        "/add Desk Calendar — коллекция (gift name)\n"
        "/del Desk Calendar\n"
        "/collections — список\n"
        "/interval 3 — секунды между сканами\n"
        "/test — проверить API\n"
        "/check — скан сейчас\n\n"
        "Токен Tonnel не обязателен для мониторинга.\n"
        "Без /add будет шумно — лучше добавить 3–10 коллекций.",
        parse_mode="HTML",
    )


@dp.message(Command("status"))
async def cmd_status(message: Message) -> None:
    if not owner_only(message):
        return
    m = ensure_monitor()
    s = store.state
    cols = ", ".join(s.collections) if s.collections else "все (шумно)"
    err = m.last_error or "—"
    await message.answer(
        f"Мониторинг: {'ON' if s.enabled else 'OFF'}\n"
        f"Discount: {s.discount_percent:g}%\n"
        f"Max price: {s.max_price_ton:g} TON\n"
        f"Interval: {s.poll_interval:g}s\n"
        f"Collections: {cols}\n"
        f"Known floors: {len(s.floors)}\n"
        f"Alerts sent: {s.alerts_sent}\n"
        f"Last scan gifts: {m.last_scan_count}\n"
        f"Last error: {err}"
    )


@dp.message(Command("on"))
async def cmd_on(message: Message) -> None:
    if not owner_only(message):
        return
    ensure_monitor()
    await message.answer("Проверяю Tonnel API...")
    try:
        await asyncio.get_event_loop().run_in_executor(None, client.ping)
    except Exception as exc:
        await message.answer(f"API недоступен: {exc}")
        return
    store.state.enabled = True
    store.save()
    await message.answer("Мониторинг Tonnel включён.")


@dp.message(Command("off"))
async def cmd_off(message: Message) -> None:
    if not owner_only(message):
        return
    store.state.enabled = False
    store.save()
    await message.answer("Мониторинг выключен.")


@dp.message(Command("discount"))
async def cmd_discount(message: Message, command: CommandObject) -> None:
    if not owner_only(message):
        return
    try:
        value = float((command.args or "").replace(",", "."))
    except ValueError:
        await message.answer("Формат: /discount 15")
        return
    if value < 0 or value > 90:
        await message.answer("Диапазон 0..90")
        return
    store.state.discount_percent = value
    store.save()
    await message.answer(f"Алерт если цена ≤ floor − {value:g}%")


@dp.message(Command("maxprice"))
async def cmd_maxprice(message: Message, command: CommandObject) -> None:
    if not owner_only(message):
        return
    try:
        value = float((command.args or "").replace(",", "."))
    except ValueError:
        await message.answer("Формат: /maxprice 5")
        return
    if value < 0:
        await message.answer("Цена не может быть отрицательной")
        return
    store.state.max_price_ton = value
    store.save()
    if value == 0:
        await message.answer("Потолок цены выключен")
    else:
        await message.answer(f"Алерт также если цена ≤ {value:g} TON")


@dp.message(Command("interval"))
async def cmd_interval(message: Message, command: CommandObject) -> None:
    if not owner_only(message):
        return
    try:
        value = float((command.args or "").replace(",", "."))
    except ValueError:
        await message.answer("Формат: /interval 3")
        return
    if value < 1 or value > 120:
        await message.answer("Диапазон 1..120 секунд")
        return
    store.state.poll_interval = value
    store.save()
    await message.answer(f"Интервал: {value:g}s")


@dp.message(Command("add"))
async def cmd_add(message: Message, command: CommandObject) -> None:
    if not owner_only(message):
        return
    name = (command.args or "").strip()
    if not name:
        await message.answer("Формат: /add Desk Calendar")
        return
    existing = {c.lower() for c in store.state.collections}
    if name.lower() in existing:
        await message.answer("Уже в списке")
        return
    store.state.collections.append(name)
    store.save()
    await message.answer(f"Добавлено: {name}")


@dp.message(Command("del"))
async def cmd_del(message: Message, command: CommandObject) -> None:
    if not owner_only(message):
        return
    name = (command.args or "").strip().lower()
    if not name:
        await message.answer("Формат: /del Desk Calendar")
        return
    before = len(store.state.collections)
    store.state.collections = [c for c in store.state.collections if c.lower() != name]
    store.save()
    if len(store.state.collections) == before:
        await message.answer("Не найдено")
    else:
        await message.answer("Удалено")


@dp.message(Command("collections"))
async def cmd_collections(message: Message) -> None:
    if not owner_only(message):
        return
    if not store.state.collections:
        await message.answer("Список пуст → мониторю всё (будет много алертов).")
        return
    await message.answer(
        "Коллекции:\n" + "\n".join(f"• {c}" for c in store.state.collections)
    )


@dp.message(Command("test"))
async def cmd_test(message: Message) -> None:
    if not owner_only(message):
        return
    await message.answer("Проверяю Tonnel API...")

    def _fetch() -> list[GiftDeal]:
        name = store.state.collections[0] if store.state.collections else None
        deals = client.search(gift_name=name, newest=False, limit=5)
        if name:
            floor = client.collection_floor(name)
            if floor is not None:
                store.state.floors[name.lower()] = floor
                store.save()
                return [
                    GiftDeal(
                        id=d.id,
                        title=d.title,
                        collection=d.collection,
                        model=d.model,
                        backdrop=d.backdrop,
                        symbol=d.symbol,
                        number=d.number,
                        price_ton=d.price_ton,
                        floor_ton=floor,
                        discount_pct=(1 - d.price_ton / floor) * 100 if floor else None,
                        link=d.link,
                        raw=d.raw,
                    )
                    for d in deals
                ]
        return deals

    try:
        gifts = await asyncio.get_event_loop().run_in_executor(None, _fetch)
    except Exception as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    if not gifts:
        await message.answer("API ок, но список пуст.")
        return

    lines = ["API ок. Примеры лотов:"]
    for deal in gifts[:5]:
        mark = ""
        if is_lol_price(deal, store.state.discount_percent, store.state.max_price_ton):
            mark = " 🔥"
        floor = f"{deal.floor_ton:.4f}" if deal.floor_ton is not None else "?"
        disc = f"{deal.discount_pct:.1f}%" if deal.discount_pct is not None else "?"
        lines.append(
            f"• {deal.display_name} — {deal.price_ton:.4f} TON "
            f"(floor {floor}, {disc}){mark}"
        )
    await message.answer("\n".join(lines))


@dp.message(Command("check"))
async def cmd_check(message: Message) -> None:
    if not owner_only(message):
        return
    m = ensure_monitor()
    await message.answer("Сканирую Tonnel...")

    def _check() -> tuple[int, list[GiftDeal]]:
        name = store.state.collections[0] if store.state.collections else None
        gifts = client.search(gift_name=name, newest=False, limit=20)
        if name:
            floor = client.collection_floor(name) or store.state.floors.get(name.lower())
        else:
            floor = None
        deals: list[GiftDeal] = []
        for g in gifts:
            key = g.collection.lower()
            f = floor if name else store.state.floors.get(key)
            if f is None and not name:
                # approximate: use min in batch for same name
                same = [x.price_ton for x in gifts if x.collection.lower() == key]
                f = min(same) if same else None
            enriched = GiftDeal(
                id=g.id,
                title=g.title,
                collection=g.collection,
                model=g.model,
                backdrop=g.backdrop,
                symbol=g.symbol,
                number=g.number,
                price_ton=g.price_ton,
                floor_ton=f,
                discount_pct=(1 - g.price_ton / f) * 100 if f else None,
                link=g.link,
                raw=g.raw,
            )
            if is_lol_price(
                enriched, store.state.discount_percent, store.state.max_price_ton
            ):
                deals.append(enriched)
        return len(gifts), deals

    try:
        total, deals = await asyncio.get_event_loop().run_in_executor(None, _check)
    except Exception as exc:
        await message.answer(f"Ошибка: {exc}")
        return

    m.last_scan_count = total
    if not deals:
        await message.answer(
            f"Скан ок ({total} лотов). Сейчас lol-price нет "
            f"по порогу {store.state.discount_percent:g}%."
        )
        return

    await message.answer(f"Найдено {len(deals)} lol-price. Шлю первые...")
    for deal in deals[:5]:
        if store.state.mark_seen(deal.id):
            await send_alert(deal)
            store.state.alerts_sent += 1
    store.save()


@dp.message(F.text)
async def fallback(message: Message) -> None:
    if owner_only(message):
        await message.answer("Не понял. /help")


async def main() -> None:
    ensure_monitor()
    me = await bot.get_me()
    logger.info("Bot started as @%s (Tonnel)", me.username)
    try:
        await bot.send_message(
            settings.owner_id,
            "Tonnel bot онлайн. Напиши /start → /on",
        )
    except Exception as exc:
        logger.warning("Could not DM owner on startup: %s", exc)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())