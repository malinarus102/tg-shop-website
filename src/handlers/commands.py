from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes
from src.config import Config
from src.services.shop import DRIVERS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
    [InlineKeyboardButton("🏁 Собрать браслет", web_app=WebAppInfo(url=Config.WEB_APP_URL))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏁 *Добро пожаловать в Браслетный Пит Стоп!* 🏁\n\n"
        "Собери свой уникальный браслет из звеньев команд F1 👇\n\n"
        "🌐 @alinv1xf",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Как собрать браслет:*\n\n"
        "1️⃣ Измерь размер запястья (например 17 см)\n"
        "2️⃣ К размеру прибавь 1 (17 + 1 = 18 звеньев)\n"
        "3️⃣ Выбери звенья любимых пилотов\n"
        "4️⃣ Ты можешь выбирать одного пилота несколько раз\n"
        "5️⃣ Оформи заказ\n\n"
        "💰 Стоимость: 500₽ за звено\n\n"
        "/start - Главное меню\n"
        "/drivers - Список пилотов",
        parse_mode="Markdown"
    )

async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Открыть конструктор"""
    keyboard = [
        [InlineKeyboardButton("🏁 Собрать браслет", web_app=WebAppInfo(url=Config.WEB_APP_URL))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🛍️ *Конструктор браслетов*\n\n"
        "Нажми кнопку и начни сборку!",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def show_drivers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать всех пилотов"""
    text = "🏁 *Пилоты Формулы-1 2024*\n\n"
    for key, driver in DRIVERS.items():
        text += f"#{driver['number']} {driver['name']} - {driver['team']}\n"
    
    text += "\n👉 /start для сборки браслета!"
    
    await update.message.reply_text(text, parse_mode="Markdown")