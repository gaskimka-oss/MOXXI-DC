import os
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, ".env"))

# Токен Discord бота (хранится в .env файле)
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN") or ""

# Префикс команд в чате Discord (помимо слэш-команд /)
PREFIXES = ["!", "m!", "."]

# Префикс ID для базы данных
# Telegram: 1..69_999_999_999
# VK: 70_000_000_000 + vk_id
# Discord: 80_000_000_000 + dc_id
# MAX: 90_000_000_000 + max_id
DISCORD_UID_OFFSET = 80_000_000_000
