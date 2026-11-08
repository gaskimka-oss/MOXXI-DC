import os
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, ".env"))

# Токен Discord бота (хранится в .env файле)
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN") or ""

# Префикс команд в чате Discord (помимо слэш-команд /)
PREFIXES = ["!", "m!", "."]

# Изолированная база данных Discord (moxxi_dc.db)
DISCORD_UID_OFFSET = 0
