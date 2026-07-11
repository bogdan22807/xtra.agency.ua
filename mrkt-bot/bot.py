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

from config import load_settings, STATE_PATH
from monitor import PriceMonitor, is_lol_price
from mrkt_client import GiftDeal, MrktClient
from storage import StateStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("mrkt-bot")

settings = load_settings()
store = StateStore(
    STATE_PATH,
    defaults={
        "mrkt_token": settings.mrkt_token,
        "discount_percent": settings.discount_percent,
        "max_price_ton": settings.max_price_ton,
        "poll_interval": settings.poll_interval,
        "enabled": False,
        "collections": [],
    },
)

bot = Bot(token=settings.bot_token)
dp = Dispatcher()
client = MrktClient(store.state.mrkt_token)
monitor: PriceMonitor | None = None
_monitor_task: asyncio.Task | None = None


def owner_only(message: Message) -> bool:
    return message.from_user is not None and message.from_user.id == settings.owner_id


def format_deal(deal: GiftDeal) -> str:
    lines = [
        "🔥 <b>LOL PRICE</b>",
        f"<b>{deal.display_name}</b>",
    ]
    if deal.collection:
        lines.append(f"Коллекция: {deal.collection}")
    if deal.model:
        lines.append(f"Модель: {deal.model}")
    if deal.backdrop:
        lines.append(f"Фон: {deal.backdrop}")
    if deal.symbol:
        lines.append(f"Узор: {deal.symbol}")

    lines.append(f"Цена: <b>{deal.price_ton:.4f} TON</b>")
    if deal.floor_ton is not None:
        lines.append(f"Floor: {deal.floor_ton:.4f} TON")
    if deal.discount_pct is not None:
        lines.append(f"Скидка к floor: <b>{deal.discount_pct:.1f}%</b>")
    lines.append(f'<a href="{deal.link}">Открыть на MRKT</a>')
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
        _monitor_task = asyncio.create_task(monitor_loop(), name="mrkt-monitor")
    return monitor


@dp.message(Command("start", "help"))
async def cmd_start(message: Message) -> None:
    if not owner_only(message):
        await message.answer("Доступ только владельцу.")
        return
    ensure_monitor()
    await message.answer(
        "MRKT sniper bot\n\n"
        "Команды:\n"
        "/token &lt;uuid&gt; — MRKT auth token\n"
        "/on — включить мониторинг\n"
        "/off — выключить\n"
        "/status — статус\n"
        "/discount 15 — % ниже floor\n"
        "/maxprice 5 — потолок цены в TON (0 = выкл)\n"
        "/add Deserter — коллекция\n"
        "/del Deserter\n"
        "/collections — список\n"
        "/interval 3 — секунды между сканами\n"
        "/test — проверить API и показать пример\n"
        "/check — скан сейчас\n\n"
        "Как взять MRKT token:\n"
        "1) web.telegram.org → @mrkt\n"
        "2) F12 → Network → auth\n"
        "3) Response → token\n"
        "4) /token &lt;вставить&gt;",
        parse_mode="HTML",
    )


@dp.message(Command("status"))
async def cmd_status(message: Message) -> None:
    if not owner_only(message):
        return
    m = ensure_monitor()
    s = store.state
    token_ok = "да" if s.mrkt_token else "нет"
    cols = ", ".join(s.collections) if s.collections else "все (шумно)"
    err = m.last_error or "—"
    await message.answer(
        f"Мониторинг: {'ON' if s.enabled else 'OFF'}\n"
        f"MRKT token: {token_ok}\n"
        f"Discount: {s.discount_percent:g}%\n"
        f"Max price: {s.max_price_ton:g} TON\n"
        f"Interval: {s.poll_interval:g}s\n"
        f"Collections: {cols}\n"
        f"Alerts sent: {s.alerts_sent}\n"
        f"Last scan gifts: {m.last_scan_count}\n"
        f"Last error: {err}"
    )


@dp.message(Command("token"))
async def cmd_token(message: Message, command: CommandObject) -> None:
    if not owner_only(message):
        return
    token = (command.args or "").strip()
    if not token:
        await message.answer("Формат: /token &lt;uuid&gt;", parse_mode="HTML")
        return
    store.state.mrkt_token = token
    store.save()
    client.set_token(token)
    try:
        await client.ping()
        await message.answer("MRKT token сохранён и работает.")
    except Exception as exc:
        await message.answer(f"Токен сохранён, но API ответил ошибкой:\n{exc}")


@dp.message(Command("on"))
async def cmd_on(message: Message) -> None:
    if not owner_only(message):
        return
    ensure_monitor()
    if not store.state.mrkt_token:
        await message.answer("Сначала /token &lt;uuid&gt;", parse_mode="HTML")
        return
    store.state.enabled = True
    store.save()
    await message.answer("Мониторинг включён.")


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
        await message.answer("Формат: /add Deserter")
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
        await message.answer("Формат: /del Deserter")
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
    await message.answer("Коллекции:\n" + "\n".join(f"• {c}" for c in store.state.collections))


@dp.message(Command("test"))
async def cmd_test(message: Message) -> None:
    if not owner_only(message):
        return
    if not store.state.mrkt_token:
        await message.answer("Сначала /token")
        return
    client.set_token(store.state.mrkt_token)
    await message.answer("Проверяю MRKT API...")
    try:
        gifts = await client.search_gifts(
            collection_names=store.state.collections[:1] if store.state.collections else [],
            ordering="Price",
            low_to_high=True,
            count=5,
        )
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
    if not store.state.mrkt_token:
        await message.answer("Сначала /token")
        return
    await message.answer("Сканирую...")
    try:
        # Force re-evaluate without priming skip for manual check of current deals
        # but still respect seen for alerts; show summary instead
        client.set_token(store.state.mrkt_token)
        gifts = await client.search_gifts(
            collection_names=store.state.collections or [],
            ordering="Price",
            low_to_high=True,
            count=20,
        )
        deals = [
            g
            for g in gifts
            if is_lol_price(g, store.state.discount_percent, store.state.max_price_ton)
        ]
        if not deals:
            await message.answer(
                f"Скан ок ({len(gifts)} лотов). Сейчас lol-price нет "
                f"по порогу {store.state.discount_percent:g}%."
            )
            return
        await message.answer(f"Найдено {len(deals)} lol-price. Шлю первые...")
        for deal in deals[:5]:
            if store.state.mark_seen(deal.id):
                await send_alert(deal)
                store.state.alerts_sent += 1
        store.save()
        m.last_scan_count = len(gifts)
    except Exception as exc:
        await message.answer(f"Ошибка: {exc}")


@dp.message(F.text)
async def fallback(message: Message) -> None:
    if owner_only(message):
        await message.answer("Не понял. /help")


async def main() -> None:
    ensure_monitor()
    me = await bot.get_me()
    logger.info("Bot started as @%s", me.username)
    try:
        await bot.send_message(
            settings.owner_id,
            "MRKT bot онлайн. Напиши /help\n"
            "Нужен MRKT token: /token &lt;uuid&gt;, потом /on",
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.warning("Could not DM owner on startup: %s", exc)
    try:
        await dp.start_polling(bot)
    finally:
        await client.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())