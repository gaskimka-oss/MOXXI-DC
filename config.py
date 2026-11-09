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

# Ссылка для приглашения и добавления бота в группы и на серверы
INVITE_URL = "https://discord.com/api/oauth2/authorize?client_id=1568910980002619402&permissions=8&scope=bot%20applications.commands"
WEBAPP_URL = "https://gaskimka-oss.github.io/MOXXI/"

