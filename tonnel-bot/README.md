# Tonnel Price Sniper Bot

Telegram-бот: ловит лоты на [Tonnel](https://market.tonnel.network) дешевле floor и шлёт алерт с названием, ценой и ссылкой.

## Быстрый старт

```bash
cd tonnel-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# заполни BOT_TOKEN и OWNER_ID
python bot.py
```

## Важно

- Для мониторинга **не нужен** Tonnel auth — API отдаёт листинги публично.
- Без `/add` будет шумно. Добавь 3–10 коллекций (точные gift name с маркета).
- Цена в API — raw; покупатель обычно платит ~+10% (бот показывает оба значения).
- Бот должен крутиться 24/7 (VPS).

## Команды

| Команда | Что делает |
|---|---|
| `/on` / `/off` | мониторинг |
| `/discount 15` | алерт если цена ≤ floor−15% |
| `/maxprice 5` | алерт если цена ≤ 5 TON |
| `/add Desk Calendar` | фильтр коллекции |
| `/test` | проверка API |
| `/check` | ручной скан |
