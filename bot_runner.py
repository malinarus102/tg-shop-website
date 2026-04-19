import requests
import os

token = os.getenv("BOT_TOKEN", "")
if token:
    requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true")

from src.bot import main

if __name__ == '__main__':
    main()