# MRKT Price Sniper Bot

Telegram-бот: в реальном времени ловит лоты на MRKT дешевле floor и шлёт алерт с названием, ценой и ссылкой.

## Быстрый старт

```bash
cd mrkt-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# заполни BOT_TOKEN и OWNER_ID
python bot.py
```

## .env

- `BOT_TOKEN` — токен от @BotFather
- `OWNER_ID` — твой Telegram id
- `MRKT_TOKEN` — опционально (можно задать командой `/token`)
- `DISCOUNT_PERCENT` — % ниже floor (по умолчанию 15)
- `MAX_PRICE_TON` — жёсткий потолок цены (0 = выкл)
- `POLL_INTERVAL` — секунды между сканами

## Как взять MRKT token

1. Открой https://web.telegram.org
2. Зайди в @mrkt (мини-приложение)
3. F12 → Network → найди `auth`
4. В Response скопируй `token`
5. В боте: `/token <вставить>` → `/on`

Токен живёт долго, но если API начнёт отвечать 401 — обнови.

## Команды

| Команда | Что делает |
|---|---|
| `/token <uuid>` | сохранить MRKT auth |
| `/on` / `/off` | мониторинг |
| `/discount 15` | алерт если цена ≤ floor−15% |
| `/maxprice 5` | алерт если цена ≤ 5 TON |
| `/add Name` | фильтр коллекции |
| `/test` | проверка API |
| `/check` | ручной скан |

## Важно

- Бот должен крутиться 24/7 (VPS / сервер).
- Без коллекций (`/add`) будет много шума.
- Токен бота не коммить в git.