# NOMINATION F1 BRACELETS BOT

Telegram-бот и веб-конструктор браслетов Formula 1.

## Что умеет проект

- запуск Telegram-бота с командами `/start`, `/help`, `/drivers`, `/catalog`;
- открытие WebApp-конструктора браслета из Telegram;
- оформление заказа и отправка уведомления администратору;
- локальная админка заказов: просмотр, изменение статуса, удаление.

## Технологии

- Python 3.11+
- Flask
- python-telegram-bot
- requests
- gunicorn

## Быстрый запуск (локально)

1) Установить зависимости:

```bash
python3 -m pip install -r requirements.txt
```

2) Создать `.env` в корне проекта:

```env
BOT_TOKEN=your_bot_token
WEB_APP_URL=https://your-ngrok-url.ngrok-free.app
ADMIN_CHAT_ID=your_admin_chat_id
ADMIN_ID=your_admin_chat_id
ADMIN_PASSWORD=change_me
```

3) Запустить веб-сервис:

```bash
python3 src/web_app.py
```

4) Если работаешь локально, поднять HTTPS туннель:

```bash
ngrok http 8080
```

5) Запустить бота:

```bash
python3 -m src.bot
```

## Переменные окружения

- `BOT_TOKEN` - токен Telegram-бота;
- `WEB_APP_URL` - HTTPS URL WebApp (например, ngrok URL);
- `ADMIN_CHAT_ID` - чат ID администратора (для worker/бота);
- `ADMIN_ID` - чат ID администратора (используется web-сервисом);
- `ADMIN_PASSWORD` - пароль для входа в `/admin`;
- `LOGGING_LEVEL` - уровень логирования, по умолчанию `INFO`.

## Запуск через Render

Проект уже подготовлен к деплою через `render.yaml`:

- `tg-shop-web` (web): `gunicorn src.web_app:app --bind 0.0.0.0:$PORT`
- `tg-shop-bot` (worker): `python -m src.bot`

Нужно только задать переменные окружения в Render Dashboard.

## Структура

```text
src/
  bot.py
  web_app.py
  config.py
  handlers/
  services/
  models/
  templates/
  pics/
```

## Важно

- не коммить `.env` и любые секреты;
- для Telegram WebApp нужен только HTTPS URL;
- при смене ngrok URL обновляй `WEB_APP_URL`.