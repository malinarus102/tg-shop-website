import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from src.config import Config
from src.handlers.commands import start, help_command, catalog, show_drivers
from src.handlers.callbacks import handle_callback

# Настройка логирования
logging.basicConfig(level=Config.LOGGING_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def handle_text(update, context):
    """Обработка текстовых сообщений"""
    text = update.message.text.strip().replace(",", ".")

    if context.user_data.get("awaiting_wrist"):
        try:
            wrist_size = float(text)
        except ValueError:
            await update.message.reply_text(
                "Введите обхват запястья числом в сантиметрах, например: 17 или 17.5"
            )
            return

        if wrist_size <= 0:
            await update.message.reply_text("Обхват должен быть больше 0 см. Попробуйте еще раз.")
            return

        links_count = int(wrist_size + 1)
        context.user_data["awaiting_wrist"] = False

        await update.message.reply_text(
            f"📏 Ваш обхват: {wrist_size:g} см\n"
            f"🔗 Ваше количество звеньев: {links_count}"
        )
        return

    await update.message.reply_text("Для нового расчета введите /start")

def main():
    """Стартуем бота"""
    from telegram.request import HTTPXRequest
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)
    application = (
        Application.builder()
        .token(Config.BOT_TOKEN)
        .request(request)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("catalog", catalog))
    application.add_handler(CommandHandler("drivers", show_drivers))

    application.add_handler(CallbackQueryHandler(handle_callback))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling()

if __name__ == '__main__':
    main()