import os

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8619719766:AAG0TIrc-DP64MS9eLi65R3Txm4K-1XnRko")
    ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "5078064482")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
    LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
    WEB_APP_URL = os.getenv("WEB_APP_URL", "https://tulip-grooving-sash.ngrok-free.dev")