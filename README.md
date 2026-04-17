# 🏁 NOMINATION F1 BRACELETS BOT

Официальный Telegram бот магазина браслетов Nomination с пилотами Формулы-1.

## ✨ Возможности

- 🛍️ **Каталог браслетов** - готовые браслеты всех 11 пилотов F1
- 🛠️ **Конструктор браслета** - собери свой уникальный браслет из звеньев
- 💳 **Оформление заказа** - быстрое и удобное оформление
- 🌐 **Веб-приложение** - красивый интерфейс в отдельном окне

## 📋 Требования

- Python 3.9+
- pip3

## 🚀 Установка и запуск

### 1. Клонируй репозиторий или распакуй архив

```bash
cd tg-shop-bot
```

### 2. Установи зависимости

```bash
python3 -m pip install -r requirements.txt
```

### 3. Запусти Flask веб-приложение (Терминал 1)

```bash
python3 src/web_app.py
```

Должно вывести:
```
* Running on http://127.0.0.1:8080
```

### 4. Запусти ngrok для HTTPS туннеля (Терминал 2)

```bash
ngrok http 8080
```

Скопируй HTTPS URL (например: `https://abc123.ngrok-free.dev`)

### 5. Обнови конфигурацию (Терминал 1)

Открой `src/config.py` и замени URL:

```python
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://abc123.ngrok-free.dev")
```

### 6. Запусти Telegram бота (Терминал 3)

```bash
python3 -m src.bot
```

Готово! Бот запущен! 🎉

## 📱 Использование

1. Напиши боту `/start`
2. Нажми кнопку **"🏁 Открыть магазин"**
3. Выбери готовый браслет или собери свой:
   - **🛍️ Готовые браслеты** - каталог с браслетами пилотов
   - **🛠️ Собрать браслет** - выбери до 11 звеньев и оформи заказ

## 📂 Структура проекта

```
tg-shop-bot/
├── src/
│   ├── bot.py                 # Главный файл бота
│   ├── config.py              # Конфигурация
│   ├── web_app.py             # Flask веб-приложение
│   ├── handlers/
│   │   ├── commands.py        # Команды бота (/start, /help)
│   │   └── callbacks.py       # Обработчики нажатий кнопок
│   ├── services/
│   │   └── shop.py            # Логика магазина (товары, пилоты)
│   ├── models/
│   │   └── product.py         # Модели данных
│   ├── templates/
│   │   └── catalog.html       # Веб-интерфейс каталога
│   └── pics/                  # Папка с фотографиями
├── requirements.txt           # Зависимости Python
└── README.md                  # Этот файл
```

## ⚙️ Конфигурация

### Переменные окружения

Создай `.env` файл или передай переменные:

```bash
BOT_TOKEN=твой_токен_от_botfather
ADMIN_CHAT_ID=твой_id
WEB_APP_URL=https://твой-ngrok-url.ngrok-free.dev
```

### src/config.py

```python
class Config:
    BOT_TOKEN = "8619719766:AAG0TIrc-DP64MS9eLi65R3Txm4K-1XnRko"
    ADMIN_CHAT_ID = "5078064482"
    WEB_APP_URL = "https://tulip-grooving-sash.ngrok-free.dev"
```

## 🏁 Пилоты Формулы-1 (2024)

Доступные пилоты в конструкторе браслета:

| № | Пилот | Команда |
|---|-------|--------|
| 1 | Max Verstappen | Red Bull |
| 81 | Lando Norris | McLaren |
| 81 | Oscar Piastri | McLaren |
| 16 | Charles Leclerc | Ferrari |
| 55 | Carlos Sainz | Ferrari |
| 44 | Lewis Hamilton | Mercedes |
| 63 | George Russell | Mercedes |
| 14 | Fernando Alonso | Aston Martin |
| 18 | Lance Stroll | Aston Martin |
| 22 | Yuki Tsunoda | AlphaTauri |
| 27 | Nico Hulkenberg | Haas |

## 💰 Цены

- **Готовый браслет**: 2500₽
- **Звено для браслета**: 500₽ за штуку

## 🔗 Ссылки

- **Instagram**: [@alinv1xf](https://instagram.com/alinv1xf)
- **Telegram Bot**: [@F1CasualWearBot](https://t.me/F1CasualWearBot)

## 🛠️ Технологический стек

- **Python 3.9+** - язык программирования
- **python-telegram-bot 20+** - библиотека для работы с Telegram API
- **Flask 2.3** - веб-фреймворк
- **ngrok** - создание HTTPS туннеля для локального сервера

## 📝 Команды бота

| Команда | Описание |
|---------|---------|
| `/start` | Главное меню с кнопкой открытия магазина |
| `/help` | Справка по командам |
| `/drivers` | Список всех пилотов Формулы-1 |
| `/catalog` | Открыть каталог браслетов |

## ⚠️ Важно

- Бот требует **HTTPS URL** для веб-приложения (используй ngrok для локальной разработки)
- ngrok бесплатный, но требует регистрации
- При перезапуске ngrok URL может измениться - обнови `config.py`

## 🐛 Решение проблем

### Ошибка "Port already in use"
```bash
lsof -i :8080
kill -9 <PID>
```

### Ошибка "catalog.html not found"
Убедись, что папка `src/templates/` существует и содержит файл `catalog.html`

### Ошибка "invalid: only https links are allowed"
Проверь, что в `config.py` используется HTTPS URL от ngrok, а не `http://localhost`

## 👨‍💻 Разработка

Проект разработан для магазина браслетов NOMINATION F1 BRACELETS.

Контакты:
- 📱 Instagram: [@alinv1xf](https://instagram.com/alinv1xf)
- 💬 Telegram: [@alinv1xf](https://t.me/alinv1xf)

---

**Версия**: 1.0.0  
**Дата**: 17 апреля 2026  
**Лицензия**: MIT