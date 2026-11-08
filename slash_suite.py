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

    # ═══════════════════════════════════════════════════════════════
    # 1. ПОМОЩЬ / HELP
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="помощь", description="📖 Справочник всех 415+ команд MOXXI и навигация")
    async def cmd_help(self, inter: disnake.ApplicationCommandInteraction):
        # We import HelpView from main
        from main import HelpView
        embed = disnake.Embed(
            title="🎮 MOXXI 3.0 ULTIMATE DISCORD",
            description=(
                "Добро пожаловать в центр управления MOXXI!\n\n"
                "**Все модули и возможности системы:**\n"
                "• ⛏ **Minecraft Модуль** — мониторинг серверов, 3D скины, верификация\n"
                "• 🏆 **Уровни и Опыт (XP)** — активность в чате, ранги и лидерборды\n"
                "• 🎉 **Розыгрыши** — интерактивные конкурсы с таймерами и кнопками\n"
                "• 🛡 **Модерация и Аудит** — быстрая модерация, варны, муты и чистка чата\n"
                "• 💼 **Карьера и Экономика** — работа, банк, грабежи, магазин предметов\n"
                "• 🎫 **Служба Поддержки** — тикеты и персональные обращения\n"
                "• 🟩 **Словесная Игра (Вордл)** — мини-игра со словами 🟩🟨⬛ с призами\n\n"
                "💡 *Команды работают как со слэшем (`/команда`), так и просто текстом в чат без слэша!*"
            ),
            color=disnake.Color.blurple()
        )
        embed.set_footer(text="MOXXI 3.0 • Выберите категорию ниже:")
        await inter.response.send_message(embed=embed, view=HelpView())

    # ═══════════════════════════════════════════════════════════════
    # 2. ПРОФИЛЬ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="профиль", description="👤 Ваш профиль, уровень, баланс, банк, ранг и статус")
    async def cmd_profile(
        self,
        inter: disnake.ApplicationCommandInteraction,
        участник: Optional[disnake.Member] = None
    ):
        target = участник or inter.author
        t_uid = config.DISCORD_UID_OFFSET + target.id
        await db.ensure_user(t_uid, username=str(target), first_name=target.display_name)
        u_data = await db.get_user(t_uid) or {}

        bal = u_data.get("balance", 0)
        bank = u_data.get("bank", 0)
        xp = u_data.get("xp", 0)
        mc_nick = u_data.get("mc_nick") or "Не привязан"

        # Level math: starts at Lv. 1
        lvl = max(1, int((xp / 100) ** 0.5) + 1)
        prev_lvl_xp = ((lvl - 1) ** 2) * 100
        next_lvl_xp = (lvl ** 2) * 100
        xp_needed = max(1, next_lvl_xp - prev_lvl_xp)
        xp_in_lvl = max(0, xp - prev_lvl_xp)
        percent = int((xp_in_lvl / xp_needed) * 100)
        p_bar = build_bar(xp_in_lvl, xp_needed, 10)

        # Buffs
        now = int(time.time())
        safe_left = u_data.get("safe_until", 0) - now
        safe_str = f"🛡 До <t:{u_data.get('safe_until', 0)}:R>" if safe_left > 0 else "❌ Неактивен"

        boost_left = u_data.get("xp_booster_until", 0) - now
        boost_str = f"⚡️ 2x до <t:{u_data.get('xp_booster_until', 0)}:R>" if boost_left > 0 else "❌ Неактивен"

        embed = disnake.Embed(
            title=f"👤 Профиль игрока — {target.display_name}",
            color=disnake.Color.gold()
        )
        if target.avatar:
            embed.set_thumbnail(url=target.avatar.url)

        embed.add_field(name="💰 Баланс", value=f"`{bal:,}` 🌑", inline=True)
        embed.add_field(name="🏦 В банке", value=f"`{bank:,}` 🌑", inline=True)
        embed.add_field(name="🏆 Уровень и Опыт", value=f"**Уровень {lvl}** • `{xp:,} XP`\n`[{p_bar}]` {xp_in_lvl}/{xp_needed} XP ({percent}%)", inline=False)
        embed.add_field(name="⛏ Minecraft", value=f"`{mc_nick}`", inline=True)
        embed.add_field(name="🛡 Сейф", value=safe_str, inline=True)
        embed.add_field(name="⚡️ Бустер опыта", value=boost_str, inline=True)

        await inter.response.send_message(embed=embed)

    # ═══════════════════════════════════════════════════════════════
    # 3. БАЛАНС
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="баланс", description="💰 Проверить свой баланс монет и банковский вклад")
    async def cmd_balance(
        self,
        inter: disnake.ApplicationCommandInteraction,
        участник: Optional[disnake.Member] = None
    ):
        target = участник or inter.author
        t_uid = config.DISCORD_UID_OFFSET + target.id
        await db.ensure_user(t_uid, username=str(target), first_name=target.display_name)
        u_data = await db.get_user(t_uid) or {}

        bal = u_data.get("balance", 0)
        bank = u_data.get("bank", 0)
        embed = disnake.Embed(
            title=f"💰 Финансы — {target.display_name}",
            description=f"💵 **На руках:** `{bal:,}` 🌑 монет\n🏦 **В банке:** `{bank:,}` 🌑 монет\n📊 **Всего:** `{bal + bank:,}` 🌑",
            color=disnake.Color.green()
        )
        await inter.response.send_message(embed=embed)

    # ═══════════════════════════════════════════════════════════════
    # 4. СЕРВЕР MINECRAFT
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="сервер", description="⛏ Проверить онлайн и статус сервера Minecraft")
    async def cmd_server(
        self,
        inter: disnake.ApplicationCommandInteraction,
        ip: Optional[str] = commands.Param(default=None, description="IP адрес или домен сервера Minecraft (например: play.myserver.ru)")
    ):
        if not ip:
            embed = disnake.Embed(
                title="⛏ Мониторинг серверов Minecraft",
                description=(
                    "Чтобы узнать статус и онлайн сервера, укажите его IP-адрес:\n\n"
                    "📌 **Как пользоваться командой:**\n"
                    "• **Слэш-команда:** `/сервер ip:адрес_сервера`\n"
                    "• **Текстом в чат:** `сервер адрес_сервера` или `пинг адрес_сервера`\n\n"
                    "🔍 *Пример:* `/сервер ip:play.myserver.ru` или `сервер 127.0.0.1:25565`\n\n"
                    "📊 *Бот в реальном времени покажет онлайн игроков, версию, цветной MOTD и статус сервера.*"
                ),
                color=disnake.Color.blurple()
            )
            return await inter.response.send_message(embed=embed)

        await inter.response.defer()
        clean_ip = ip.strip()
        url = f"https://api.mcsrvstat.us/2/{clean_ip}"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=5.0) as resp:
                    if resp.status != 200:
                        return await inter.edit_original_response(f"❌ Ошибка получения данных сервера `{clean_ip}`!")
                    data = await resp.json()
        except Exception as e:
            return await inter.edit_original_response(f"❌ Не удалось подключиться к серверу: {e}")

        online = data.get("online", False)
        if not online:
            embed = disnake.Embed(
                title=f"🔴 Сервер Оффлайн — `{clean_ip}`",
                description="Сервер сейчас недоступен или указан неверный адрес.",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)

        p_info = data.get("players", {})
        p_online = p_info.get("online", 0)
        p_max = p_info.get("max", 0)
        version = data.get("version", "Неизвестно")
        motd_lines = data.get("motd", {}).get("clean", [])
        motd_text = "\n".join(motd_lines) if motd_lines else "Нет описания"

        embed = disnake.Embed(
            title=f"🟢 Статус Minecraft сервера — {clean_ip}",
            color=disnake.Color.green()
        )
        embed.add_field(name="👥 Онлайн", value=f"**{p_online:,}** / {p_max:,}", inline=True)
        embed.add_field(name="🏷 Версия", value=f"`{version}`", inline=True)
        embed.add_field(name="📜 Описание (MOTD)", value=f"```\n{motd_text}\n```", inline=False)
        embed.set_thumbnail(url=f"https://api.mcsrvstat.us/icon/{clean_ip}")
        await inter.edit_original_response(embed=embed)

    # ═══════════════════════════════════════════════════════════════
    # 5. СКИН MINECRAFT
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="скин", description="👕 Показать 3D модель скина игрока Minecraft")
    async def cmd_skin(
        self,
        inter: disnake.ApplicationCommandInteraction,
        ник: Optional[str] = commands.Param(default=None, description="Никнейм игрока Minecraft (например: Steve)")
    ):
        if not ник:
            embed = disnake.Embed(
                title="👕 Просмотр 3D скинов Minecraft",
                description=(
                    "Чтобы посмотреть 3D скин любого игрока, укажите его никнейм:\n\n"
                    "📌 **Как пользоваться командой:**\n"
                    "• **Слэш-команда:** `/скин ник:Steve`\n"
                    "• **Текстом в чат:** `скин Steve`"
                ),
                color=disnake.Color.blurple()
            )
            return await inter.response.send_message(embed=embed)

        clean_nick = ник.strip()
        skin_url = f"https://mc-heads.net/body/{clean_nick}/right"
        avatar_url = f"https://mc-heads.net/avatar/{clean_nick}"

        embed = disnake.Embed(
            title=f"👕 3D Скин игрока — {clean_nick}",
            color=disnake.Color.gold()
        )
        embed.set_image(url=skin_url)
        embed.set_thumbnail(url=avatar_url)
        await inter.response.send_message(embed=embed)

    # ═══════════════════════════════════════════════════════════════
    # 6. РАБОТА И КАРЬЕРА (СИНХРОНИЗИРОВАНО С ПРИЛОЖЕНИЕМ)
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="работа", description="💼 Отработать смену по вашей профессии и получить зарплату")
    async def cmd_work(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()

        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        u_data = await db.get_user(u_uid) or {}
        user_xp = u_data.get("xp", 0)
        user_lvl = max(1, int((user_xp / 100) ** 0.5) + 1)

        job_row = await db.get_user_job(u_uid)
        first_time = False

        if not job_row or not job_row.get("job_key") or job_row.get("job_key") not in KEY_TO_JOB:
            # Автоматически трудоустраиваем новичка на стартовую должность 'уборщик'
            default_key = "уборщик"
            await db.set_user_job(u_uid, default_key)
            job_row = await db.get_user_job(u_uid)
            first_time = True

        job_key = job_row["job_key"]
        job = KEY_TO_JOB[job_key]

        now = int(time.time())
        diff = now - (job_row.get("last_worked", 0) or 0)
        cd = job["cooldown"]

        if not first_time and diff < cd:
            rem = cd - diff
            rm = rem // 60
            rs = rem % 60
            embed = disnake.Embed(
                title="⏳ Смена ещё не началась!",
                description=(
                    f"Вы уже отработали прошлую смену на должности **{job['title']}**!\n\n"
                    f"⏱ Отдохните ещё **{rm} мин. {rs} сек.** перед новым выходом на работу."
                ),
                color=disnake.Color.orange()
            )
            return await inter.edit_original_response(embed=embed)

        salary = random.randint(job["min_pay"], job["max_pay"])
        xp_gain = 35

        await db.add_balance(u_uid, salary)
        await db.add_user_xp(u_uid, xp_gain)
        await db.record_job_work(u_uid, salary, now)

        first_note = "🎉 **Поздравляем с первым трудоустройством!** Вы приняты на должность дворника.\n\n" if first_time else ""
        tot = (job_row.get("total_earned", 0) or 0) + salary

        embed = disnake.Embed(
            title=f"💼 Успешная смена: {job['title']}",
            description=(
                f"{first_note}"
                f"📝 *{job['desc']}*\n\n"
                f"💰 **Заработано за смену:** `+{salary:,}` 🌑 монет\n"
                f"⚡️ **Получено опыта:** `+{xp_gain}` XP\n"
                f"📊 **Всего заработано за карьеру:** `{tot:,}` 🌑\n\n"
                f"💡 *Посмотреть список других профессий: `/работы` или `работы` в чат.*"
            ),
            color=disnake.Color.green()
        )
        await inter.edit_original_response(embed=embed)

    @commands.slash_command(name="работы", description="📋 Список доступных профессий, зарплат и требований")
    async def cmd_jobs(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        u_data = await db.get_user(u_uid) or {}
        user_xp = u_data.get("xp", 0)
        user_lvl = max(1, int((user_xp / 100) ** 0.5) + 1)

        job_row = await db.get_user_job(u_uid)
        cur_key = job_row.get("job_key") if job_row else None

        embed = disnake.Embed(
            title="💼 КАРЬЕРНАЯ ЛЕСТНИЦА MOXXI",
            description=f"👤 Ваш уровень: **Уровень {user_lvl}**\n\n"
                        f"Выберите профессию и устройтесь через `/устроиться [номер]`:\n\n",
            color=disnake.Color.blurple()
        )

        for num, j in JOBS_CATALOG.items():
            mark = " ✅ *(Ваша должность)*" if cur_key == j["key"] else ""
            status = "🔓 Доступно" if user_lvl >= j["req_lvl"] else f"🔒 Требуется {j['req_lvl']} ур."
            cd_min = j["cooldown"] // 60
            embed.add_field(
                name=f"{num}. {j['title']}{mark}",
                value=f"💵 Зарплата: `{j['min_pay']:,} - {j['max_pay']:,}` 🌑 | ⏱ Кулдаун: `{cd_min} мин.`\n"
                      f"Статус: **{status}** • *{j['desc']}*",
                inline=False
            )

        await inter.edit_original_response(embed=embed)

    @commands.slash_command(name="устроиться", description="📝 Выбрать и устроиться на профессию из списка")
    async def cmd_apply_job(
        self,
        inter: disnake.ApplicationCommandInteraction,
        профессия: Optional[str] = commands.Param(
            default=None,
            description="Выберите профессию из выпадающего списка",
            choices=[
                disnake.OptionChoice("1. 🧹 Дворник / Уборщик (150-350 🌑 | с 1 ур.)", "1"),
                disnake.OptionChoice("2. 🚴 Доставщик / Курьер (400-800 🌑 | со 2 ур.)", "2"),
                disnake.OptionChoice("3. ☕️ Бариста / Официант (900-1,600 🌑 | с 4 ур.)", "3"),
                disnake.OptionChoice("4. 🚕 Водитель такси (1,800-3,200 🌑 | с 7 ур.)", "4"),
                disnake.OptionChoice("5. 💻 IT-Программист (3,500-6,500 🌑 | с 10 ур.)", "5"),
                disnake.OptionChoice("6. 🏦 Банковский аналитик (7,000-13,000 🌑 | с 15 ур.)", "6"),
                disnake.OptionChoice("7. 🏛 Государственный советник (15,000-28,000 🌑 | с 25 ур.)", "7"),
                disnake.OptionChoice("8. 💎 Президент холдинга (35,000-65,000 🌑 | с 40 ур.)", "8"),
            ]
        )
    ):
        await inter.response.defer()
        if not профессия:
            return await self.cmd_jobs(inter)

        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        u_data = await db.get_user(u_uid) or {}
        user_xp = u_data.get("xp", 0)
        user_lvl = max(1, int((user_xp / 100) ** 0.5) + 1)

        job_str = str(профессия)
        job = JOBS_CATALOG.get(job_str) or KEY_TO_JOB.get(job_str)
        if not job:
            return await inter.edit_original_response("❌ Неверная профессия! Выберите из списка: `/работы`.")

        if user_lvl < job["req_lvl"]:
            return await inter.edit_original_response(
                f"❌ Для должности **{job['title']}** требуется минимум **{job['req_lvl']} уровень** (ваш: {user_lvl} ур.)!\n"
                f"Общайтесь в чате и играйте, чтобы повысить свой уровень."
            )

        await db.set_user_job(u_uid, job["key"])
        embed = disnake.Embed(
            title="🎉 ПОЗДРАВЛЯЕМ С ТРУДОУСТРОЙСТВОМ!",
            description=(
                f"Вы успешно назначены на должность: **{job['title']}**!\n\n"
                f"💰 **Зарплата:** `{job['min_pay']:,} - {job['max_pay']:,}` 🌑 за смену\n"
                f"⏱ **Интервал смен:** `{job['cooldown'] // 60} мин.`\n\n"
                f"👉 Чтобы выйти на работу прямо сейчас, введите: `/работа`!"
            ),
            color=disnake.Color.green()
        )
        await inter.edit_original_response(embed=embed)

    @commands.slash_command(name="уволиться", description="🚪 Уволиться с текущей работы по собственному желанию")
    async def cmd_quit_job(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.quit_user_job(u_uid)
        await inter.edit_original_response("🚪 Вы успешно уволились с работы и теперь свободны! Чтобы выбрать новую, введите: `/работы`.")

    # ═══════════════════════════════════════════════════════════════
    # 7. ПОПРОШАЙНИЧАТЬ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="попрошайничать", description="🪙 Попытать удачу и собрать мелочь на улицах")
    async def cmd_beg(self, inter: disnake.ApplicationCommandInteraction):
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        u_data = await db.get_user(u_uid) or {}

        now = int(time.time())
        last = u_data.get("last_beg_ts", 0)
        cd = 120
        if now - last < cd:
            left = cd - (now - last)
            return await inter.response.send_message(
                f"⏳ Прохожие пока не хотят давать вам мелочь! Подождите **{left} сек.**",
                ephemeral=True
            )

        earned = random.randint(10, 95)
        donors = ["Илон Маск", "Добрый незнакомец", "Бабушка у метро", "Уличный музыкант", "Мистер Бист"]
        donor = random.choice(donors)

        await db.add_balance(u_uid, earned)
        await db.update_user_action_cooldown(u_uid, "last_beg_ts", now)

        embed = disnake.Embed(
            title="🪙 Уличные подаяния",
            description=f"🎩 **{donor}** сжалился над вами и бросил в шляпу **+{earned:,} 🌑** монет!",
            color=disnake.Color.gold()
        )
        await inter.response.send_message(embed=embed)

    # ═══════════════════════════════════════════════════════════════
    # 8. КРИМИНАЛ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="криминал", description="🥷 Совершить дерзкое ограбление с риском для кошелька")
    async def cmd_crime(self, inter: disnake.ApplicationCommandInteraction):
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        u_data = await db.get_user(u_uid) or {}

        now = int(time.time())
        last = u_data.get("last_crime_ts", 0)
        cd = 600
        if now - last < cd:
            left = cd - (now - last)
            return await inter.response.send_message(
                f"🚨 Полиция всё ещё патрулирует район! Переждите **{left // 60} мин. {left % 60} сек.**",
                ephemeral=True
            )

        await db.update_user_action_cooldown(u_uid, "last_crime_ts", now)

        # 60% успех, 40% провал
        if random.random() < 0.60:
            loot = random.randint(300, 1200)
            await db.add_balance(u_uid, loot)
            embed = disnake.Embed(
                title="🥷 УСПЕШНОЕ ОГРАБЛЕНИЕ!",
                description=(
                    f"Вы взломали инкассаторский фургон и скрылись без следа!\n\n"
                    f"💰 **Ваш куш:** `+{loot:,}` 🌑 монет!"
                ),
                color=disnake.Color.green()
            )
        else:
            bal = u_data.get("balance", 0)
            fine = min(bal, random.randint(200, 500))
            if fine > 0:
                await db.add_balance(u_uid, -fine)
            embed = disnake.Embed(
                title="🚨 ОБЛАВА ПОЛИЦИИ!",
                description=(
                    f"Вас окружил спецназ прямо на месте преступления!\n\n"
                    f"⚖️ **Штраф:** `-{fine:,}` 🌑 монет."
                ),
                color=disnake.Color.red()
            )
        await inter.response.send_message(embed=embed)

    # ═══════════════════════════════════════════════════════════════
    # 9. МАГАЗИН ПРЕДМЕТОВ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="магазин", description="🛒 Витрина предметов, защитных сейфов и бустеров")
    async def cmd_shop(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        embed = disnake.Embed(
            title="🛒 МАГАЗИН ПРЕДМЕТОВ MOXXI",
            description=(
                "Выберите предмет для покупки из выпадающего списка `/купить [товар]` "
                "или нажмите на кнопку под этим сообщением:\n\n"
                "**1.** 🛡 **Сейф от грабителей** — `5,000` 🌑\n"
                "   *100% иммунитет от любых краж на 7 дней!*\n\n"
                "**2.** ⚡️ **Бустер опыта 2x** — `2,500` 🌑\n"
                "   *Удваивает весь получаемый XP в чате на 24 часа!*\n\n"
                "**3.** 🎫 **Лотерейный билет** — `500` 🌑\n"
                "   *Шанс выиграть джекпот в ежедневном тираже!*\n\n"
                "**4.** ⛏ **Набор шахтёра** — `1,500` 🌑\n"
                "   *Увеличивает добычу руды в шахте на 50%!*"
            ),
            color=disnake.Color.blurple()
        )
        view = disnake.ui.View(timeout=None)
        view.add_item(disnake.ui.Button(style=disnake.ButtonStyle.primary, label="🛡 Сейф (5,000 🌑)", custom_id="dc_shop_buy:safe"))
        view.add_item(disnake.ui.Button(style=disnake.ButtonStyle.success, label="⚡️ Бустер 2x (2,500 🌑)", custom_id="dc_shop_buy:booster"))
        view.add_item(disnake.ui.Button(style=disnake.ButtonStyle.secondary, label="🎫 Лотерея (500 🌑)", custom_id="dc_shop_buy:lottery"))
        view.add_item(disnake.ui.Button(style=disnake.ButtonStyle.secondary, label="⛏ Шахтёр (1,500 🌑)", custom_id="dc_shop_buy:miner"))
        await inter.edit_original_response(embed=embed, view=view)

    # ═══════════════════════════════════════════════════════════════
    # 10. КУПИТЬ ПРЕДМЕТ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="купить", description="💳 Купить предмет или улучшение в магазине")
    async def cmd_buy(
        self,
        inter: disnake.ApplicationCommandInteraction,
        товар: Optional[str] = commands.Param(
            default=None,
            description="Выберите предмет для покупки из списка",
            choices=[
                disnake.OptionChoice("🛡 Сейф от грабителей (5,000 🌑) — защита на 7 дней", "safe"),
                disnake.OptionChoice("⚡️ Бустер опыта 2x (2,500 🌑) — удвоение XP на 24 часа", "booster"),
                disnake.OptionChoice("🎫 Лотерейный билет (500 🌑) — билет на тираж", "lottery"),
                disnake.OptionChoice("⛏ Набор шахтёра (1,500 🌑) — +50% к добыче в шахте", "miner"),
            ]
        )
    ):
        await inter.response.defer()
        if not товар:
            return await self.cmd_shop(inter)

        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        u_data = await db.get_user(u_uid) or {}
        bal = u_data.get("balance", 0)
        now = int(time.time())

        # Match item
        t_key = str(товар).lower()
        if t_key in ("1", "safe", "сейф"):
            price = 5000
            if bal < price:
                return await inter.edit_original_response(f"❌ Недостаточно средств! Нужно `{price:,}` 🌑, а у вас `{bal:,}` 🌑.")
            await db.add_balance(u_uid, -price)
            until = max(now, u_data.get("safe_until", 0)) + 7 * 86400
            await db.set_user_safe(u_uid, until)
            embed = disnake.Embed(
                title="🛡 ПОКУПКА УСПЕШНА!",
                description=f"Вы приобрели **Сейф от грабителей**!\n\n🔒 Ваш кошелёк защищён от ограблений до <t:{until}:F> (<t:{until}:R>)!\n💰 Списано: `-{price:,}` 🌑.",
                color=disnake.Color.green()
            )
            return await inter.edit_original_response(embed=embed)

        elif t_key in ("2", "booster", "бустер"):
            price = 2500
            if bal < price:
                return await inter.edit_original_response(f"❌ Недостаточно средств! Нужно `{price:,}` 🌑, а у вас `{bal:,}` 🌑.")
            await db.add_balance(u_uid, -price)
            until = max(now, u_data.get("xp_booster_until", 0)) + 86400
            await db.set_user_xp_booster(u_uid, until)
            embed = disnake.Embed(
                title="⚡️ ПОКУПКА УСПЕШНА!",
                description=f"Вы активировали **Бустер опыта 2x**!\n\n🚀 Весь получаемый XP в чате удваивается до <t:{until}:F> (<t:{until}:R>)!\n💰 Списано: `-{price:,}` 🌑.",
                color=disnake.Color.green()
            )
            return await inter.edit_original_response(embed=embed)

        elif t_key in ("3", "lottery", "билет", "лотерея"):
            price = 500
            if bal < price:
                return await inter.edit_original_response(f"❌ Недостаточно средств! Нужно `{price:,}` 🌑, а у вас `{bal:,}` 🌑.")
            await db.add_balance(u_uid, -price)
            embed = disnake.Embed(
                title="🎫 ПОКУПКА УСПЕШНА!",
                description=f"Вы приобрели **Лотерейный билет**!\n\n🎉 Желаем удачи в ближайшем тираже джекпота!\n💰 Списано: `-{price:,}` 🌑.",
                color=disnake.Color.green()
            )
            return await inter.edit_original_response(embed=embed)

        elif t_key in ("4", "miner", "шахтер", "шахтёр", "кирка"):
            price = 1500
            if bal < price:
                return await inter.edit_original_response(f"❌ Недостаточно средств! Нужно `{price:,}` 🌑, а у вас `{bal:,}` 🌑.")
            await db.add_balance(u_uid, -price)
            embed = disnake.Embed(
                title="⛏ ПОКУПКА УСПЕШНА!",
                description=f"Вы приобрели **Набор шахтёра**!\n\n💎 Добыча ценных ресурсов в шахте увеличена на 50%!\n💰 Списано: `-{price:,}` 🌑.",
                color=disnake.Color.green()
            )
            return await inter.edit_original_response(embed=embed)

        else:
            return await inter.edit_original_response("❌ Неизвестный товар! Посмотрите витрину: `/магазин`.")

    # ═══════════════════════════════════════════════════════════════
    # 11. ИНВЕНТАРЬ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="инвентарь", description="🎒 Просмотр предметов и активных баффов")
    async def cmd_inventory(self, inter: disnake.ApplicationCommandInteraction):
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        u_data = await db.get_user(u_uid) or {}

        now = int(time.time())
        safe_left = u_data.get("safe_until", 0) - now
        safe_str = f"🛡 Активен (до <t:{u_data.get('safe_until', 0)}:R>)" if safe_left > 0 else "❌ Не приобретён"

        boost_left = u_data.get("xp_booster_until", 0) - now
        boost_str = f"⚡️ Активен 2x (до <t:{u_data.get('xp_booster_until', 0)}:R>)" if boost_left > 0 else "❌ Не приобретён"

        embed = disnake.Embed(
            title=f"🎒 Инвентарь игрока — {inter.author.display_name}",
            color=disnake.Color.blurple()
        )
        embed.add_field(name="🛡 Сейф от грабителей", value=safe_str, inline=False)
        embed.add_field(name="⚡️ Бустер опыта (2x XP)", value=boost_str, inline=False)
        embed.add_field(name="⛏ Привязанный Minecraft", value=f"`{u_data.get('mc_nick') or 'Не привязан'}`", inline=False)

        await inter.response.send_message(embed=embed)

    # ═══════════════════════════════════════════════════════════════
    # 12. РОЗЫГРЫШ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="розыгрыш", description="🎉 Запустить интерактивный розыгрыш призов")
    async def cmd_giveaway(
        self,
        inter: disnake.ApplicationCommandInteraction,
        минут: int = commands.Param(default=5, ge=1, le=1440, description="Длительность розыгрыша в минутах"),
        победителей: int = commands.Param(default=1, ge=1, le=20, description="Количество победителей"),
        приз: str = commands.Param(default="1000 монет", description="Название или сумма приза")
    ):
        ends_at = int(time.time()) + (минут * 60)
        embed = disnake.Embed(
            title="🎉 РОЗЫГРЫШ ПРИЗОВ! 🎉",
            description=(
                f"🎁 **Приз:** **{приз}**\n"
                f"👑 **Победителей:** `{победителей}`\n"
                f"👤 **Организатор:** {inter.author.mention}\n"
                f"⏳ **Окончание:** <t:{ends_at}:R> (<t:{ends_at}:T>)\n\n"
                f"👉 *Нажмите на кнопку ниже, чтобы принять участие!*"
            ),
            color=disnake.Color.gold()
        )

        gw_id = await db.create_giveaway(
            channel_id=inter.channel.id,
            message_id=0,
            prize=приз,
            winners_count=победителей,
            ends_at=ends_at,
            created_by=inter.author.id
        )

        join_btn = disnake.ui.Button(
            style=disnake.ButtonStyle.success,
            label="🎉 Участвовать (0)",
            custom_id=f"dc_gw_join:{gw_id}"
        )
        view = disnake.ui.View(timeout=None)
        view.add_item(join_btn)

        await inter.response.send_message(embed=embed, view=view)
        msg = await inter.original_response()
        await db.conn().execute("UPDATE dc_giveaways SET message_id = ? WHERE id = ?", (msg.id, gw_id))
        await db.conn().commit()

    # ═══════════════════════════════════════════════════════════════
    # 13. ОЧИСТИТЬ ЧАТ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="очистить", description="🧹 Очистить последние сообщения в канале")
    async def cmd_clear(
        self,
        inter: disnake.ApplicationCommandInteraction,
        количество: int = commands.Param(ge=1, le=100, description="Сколько сообщений удалить (1-100)")
    ):
        if not inter.channel.permissions_for(inter.author).manage_messages:
            return await inter.response.send_message("❌ У вас нет прав на управление сообщениями!", ephemeral=True)

        await inter.response.defer(ephemeral=True)
        deleted = await inter.channel.purge(limit=количество)
        await inter.edit_original_response(f"🧹 Успешно удалено **{len(deleted)}** сообщений!")

    # ═══════════════════════════════════════════════════════════════
    # 14. СЕРВЕР ИНФО
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="сервер_инфо", description="📊 Досье и статистика сервера")
    async def cmd_serverinfo(self, inter: disnake.ApplicationCommandInteraction):
        guild = inter.guild
        if not guild:
            return await inter.response.send_message("❌ Доступно только на сервере!", ephemeral=True)

        embed = disnake.Embed(
            title=f"📊 Досье сервера: {guild.name}",
            color=disnake.Color.blurple()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        created_ts = int(guild.created_at.timestamp())
        embed.add_field(name="👑 Владелец", value=f"{guild.owner.mention if guild.owner else 'Неизвестен'}", inline=True)
        embed.add_field(name="👥 Участников", value=f"`{guild.member_count}`", inline=True)
        embed.add_field(name="💬 Каналов", value=f"`{len(guild.channels)}`", inline=True)
        embed.add_field(name="🎭 Ролей", value=f"`{len(guild.roles)}`", inline=True)
        embed.add_field(name="📅 Создан", value=f"<t:{created_ts}:D> (<t:{created_ts}:R>)", inline=True)
        embed.set_footer(text=f"ID: {guild.id}")

        await inter.response.send_message(embed=embed)

    # ═══════════════════════════════════════════════════════════════
    # 15. ТИКЕТ В ТЕХПОДДЕРЖКУ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="тикет", description="📩 Открыть тикет в службу поддержки сервера")
    async def cmd_ticket(
        self,
        inter: disnake.ApplicationCommandInteraction,
        тема: str = commands.Param(description="Опишите ваш вопрос или проблему")
    ):
        from main import DiscordTicketView
        tid = await db.create_support_ticket(
            user_id=config.DISCORD_UID_OFFSET + inter.author.id,
            user_name=str(inter.author),
            text=тема,
            status="open",
            platform="discord",
            platform_peer_id=inter.channel.id
        )

        embed = disnake.Embed(
            title=f"🆘 ТИКЕТ В ПОДДЕРЖКУ #{tid}",
            description=(
                f"👤 **Игрок:** {inter.author.mention}\n"
                f"❓ **Вопрос:**\n```\n{html.escape(тема)}\n```\n"
                f"⏳ **Статус:** Ожидает сотрудника\n"
                f"⏱ *Если модератор не ответит за 1 час, тикет автоматически освободится.*"
            ),
            color=disnake.Color.gold()
        )
        view = DiscordTicketView(ticket_id=tid)
        await inter.channel.send(embed=embed, view=view)
        await inter.response.send_message(f"✅ Ваш тикет **#{tid}** успешно создан и отправлен модераторам!", ephemeral=True)

    # ═══════════════════════════════════════════════════════════════
    # 16. ПАНЕЛЬ ВЕРИФИКАЦИИ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="панель_верификации", description="🛡 Создать панель верификации с кнопкой")
    async def cmd_verify_panel(
        self,
        inter: disnake.ApplicationCommandInteraction,
        роль: disnake.Role = commands.Param(description="Роль, выдаваемая при верификации")
    ):
        if not inter.channel.permissions_for(inter.author).administrator:
            return await inter.response.send_message("❌ Только администратор может создавать панель верификации!", ephemeral=True)

        embed = disnake.Embed(
            title="🛡 ВЕРИФИКАЦИЯ НА СЕРВЕРЕ",
            description=(
                f"Добро пожаловать на сервер **{inter.guild.name}**!\n\n"
                f"Чтобы получить доступ к каналам и роли {роль.mention}, "
                f"нажмите на зелёную кнопку ниже:"
            ),
            color=disnake.Color.green()
        )
        btn = disnake.ui.Button(
            style=disnake.ButtonStyle.success,
            label="✅ Пройти верификацию",
            custom_id=f"dc_verify:{роль.id}"
        )
        view = disnake.ui.View(timeout=None)
        view.add_item(btn)

        await inter.channel.send(embed=embed, view=view)
        await inter.response.send_message("✅ Панель верификации успешно создана!", ephemeral=True)

    # ═══════════════════════════════════════════════════════════════
    # 17. ПАНЕЛЬ ТИКЕТОВ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="панель_тикетов", description="🎫 Создать интерактивную панель поддержки")
    async def cmd_ticket_panel(self, inter: disnake.ApplicationCommandInteraction):
        if not inter.channel.permissions_for(inter.author).administrator:
            return await inter.response.send_message("❌ Только администратор может создавать панель тикетов!", ephemeral=True)

        embed = disnake.Embed(
            title="🎫 СЛУЖБА ПОДДЕРЖКИ СЕРВЕРА",
            description=(
                "Возникли вопросы, проблемы или предложения?\n\n"
                "Нажмите на кнопку ниже, чтобы моментально открыть личное обращение к модерации сервера!"
            ),
            color=disnake.Color.blurple()
        )
        btn = disnake.ui.Button(
            style=disnake.ButtonStyle.primary,
            label="📩 Открыть тикет",
            custom_id="dc_open_ticket_panel"
        )
        view = disnake.ui.View(timeout=None)
        view.add_item(btn)

        await inter.channel.send(embed=embed, view=view)
        await inter.response.send_message("✅ Панель поддержки успешно создана!", ephemeral=True)

    # ═══════════════════════════════════════════════════════════════
    # 18. ВОРДЛ / WORDLE (Wordle Game 🟩🟨⬛)
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="вордл", description="🟩 Мини-игра Wordle: угадайте слово из 5 букв за 6 попыток!")
    async def cmd_wordle(
        self,
        inter: disnake.ApplicationCommandInteraction,
        слово: Optional[str] = commands.Param(default=None, description="Ваша догадка из 5 букв (например: поезд)")
    ):
        user_id = inter.author.id
        if not слово:
            # Начать игру или показать текущее состояние
            sess = wordle_game.get_wordle_session(user_id)
            if not sess:
                sess = wordle_game.start_wordle_session(user_id)
            board_text = wordle_game.render_board(sess)
            embed = disnake.Embed(
                title="🟩 ИГРА ВОРДЛ (Wordle)",
                description=(
                    f"Загадано секретное русское слово из **5 букв**!\n"
                    f"У вас есть **6 попыток**, чтобы его разгадать.\n\n"
                    f"{board_text}\n\n"
                    f"💡 Чтобы сделать ход, напишите: `/вордл [слово]` или `вордл [слово]` в чат!"
                ),
                color=disnake.Color.blurple()
            )
            return await inter.response.send_message(embed=embed)

        embed, is_won, is_over, reward = wordle_game.process_guess(user_id, слово)
        if is_won and reward > 0:
            db_uid = config.DISCORD_UID_OFFSET + user_id
            await db.add_balance(db_uid, reward)
            await db.add_user_xp(db_uid, 100)

        await inter.response.send_message(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(SlashSuite(bot))
