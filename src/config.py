import os

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
    LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
    WEB_APP_URL = os.getenv("WEB_APP_URL", "https://example.ngrok-free.app")