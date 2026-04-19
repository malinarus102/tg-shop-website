import os
import logging

logger = logging.getLogger(__name__)

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
    LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
    WEB_APP_URL = os.getenv("WEB_APP_URL", "https://example.ngrok-free.app")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

    @classmethod
    def validate(cls):
        """Проверяем критичные переменные при старте."""
        errors = []

        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN не задан")

        if not cls.ADMIN_CHAT_ID:
            errors.append("ADMIN_CHAT_ID не задан")

        if not cls.ADMIN_PASSWORD:
            errors.append("ADMIN_PASSWORD не задан")
        elif len(cls.ADMIN_PASSWORD) < 8:
            errors.append("ADMIN_PASSWORD слишком короткий — минимум 8 символов")

        if errors:
            for e in errors:
                logger.critical("❌ Конфиг: %s", e)
            raise RuntimeError(
                "Заполните .env файл перед запуском:\n" + "\n".join(f"  • {e}" for e in errors)
            )
