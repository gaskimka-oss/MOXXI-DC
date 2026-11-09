"""Slash Command Suite for MOXXI Discord Bot.
Registers native Discord Application Commands so MOXXI appears directly
for the MOXXI Discord Bot ecosystem.
"""
from __future__ import annotations

import datetime
import html
import json
import logging
import random
import time
from typing import Optional

import aiohttp
import disnake
from disnake.ext import commands

import config
import db
import wordle_game

log = logging.getLogger("moxxi-dc")

# ═══════════════════════════════════════════════════════════════
# 💼 КАТАЛОГ ПРОФЕССИЙ MOXXI
# ═══════════════════════════════════════════════════════════════
JOBS_CATALOG = {
    "1": {"key": "уборщик", "title": "🧹 Дворник / Уборщик", "req_lvl": 1, "min_pay": 150, "max_pay": 350, "cooldown": 1200, "desc": "Уборка улиц и помещений города MOXXI."},
    "2": {"key": "курьер", "title": "🚴 Доставщик / Курьер", "req_lvl": 2, "min_pay": 400, "max_pay": 800, "cooldown": 1500, "desc": "Быстрая доставка еды и ценных посылок."},
    "3": {"key": "бариста", "title": "☕️ Бариста / Официант", "req_lvl": 4, "min_pay": 900, "max_pay": 1600, "cooldown": 1800, "desc": "Варка авторского кофе и обслуживание гостей."},
    "4": {"key": "таксист", "title": "🚕 Водитель такси", "req_lvl": 7, "min_pay": 1800, "max_pay": 3200, "cooldown": 2100, "desc": "Пассажирские перевозки по неоновым улицам."},
    "5": {"key": "программист", "title": "💻 IT-Программист", "req_lvl": 10, "min_pay": 3500, "max_pay": 6500, "cooldown": 2400, "desc": "Разработка ядра, систем и модулей бота MOXXI."},
    "6": {"key": "банкир", "title": "🏦 Банковский аналитик", "req_lvl": 15, "min_pay": 7000, "max_pay": 13000, "cooldown": 2700, "desc": "Управление крупными инвестициями и вкладами."},
    "7": {"key": "депутат", "title": "🏛 Государственный советник", "req_lvl": 25, "min_pay": 15000, "max_pay": 28000, "cooldown": 3000, "desc": "Принятие законов и распределение городской казны."},
    "8": {"key": "олигарх", "title": "💎 Президент холдинга", "req_lvl": 40, "min_pay": 35000, "max_pay": 65000, "cooldown": 3600, "desc": "Руководство корпорацией и мировыми активами."},
}
KEY_TO_JOB = {j["key"]: j for j in JOBS_CATALOG.values()}


def build_bar(cur: int, total: int, length: int = 10) -> str:
    ratio = min(1.0, max(0.0, cur / total if total > 0 else 0))
    filled = int(length * ratio)
    return "▰" * filled + "▱" * (length - filled)


class SlashSuite(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_slash_command_error(self, inter: disnake.ApplicationCommandInteraction, error: Exception):
        log.error(f"Slash command '{inter.data.name}' failed: {error}", exc_info=True)
        msg = f"⚠️ Ошибка при выполнении команды: {error}"
        try:
            if inter.response.is_done():
                await inter.edit_original_response(content=msg)
            else:
                await inter.response.send_message(content=msg, ephemeral=True)
        except Exception:
            pass

    
