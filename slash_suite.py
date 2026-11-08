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


def build_bar(cur: int, total: int, length: int = 10) -> str:
    ratio = min(1.0, max(0.0, cur / total if total > 0 else 0))
    filled = int(length * ratio)
    return "█" * filled + "░" * (length - filled)


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

        # Level math
        lvl = int((xp / 100) ** 0.5) if xp > 0 else 0
        cur_lvl_xp = (lvl ** 2) * 100
        next_lvl_xp = ((lvl + 1) ** 2) * 100
        xp_needed = max(1, next_lvl_xp - cur_lvl_xp)
        xp_in_lvl = xp - cur_lvl_xp
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
        embed.add_field(name="🏆 Уровень", value=f"**Lv. {lvl}**\n`[{p_bar}]` {xp_in_lvl}/{xp_needed} XP", inline=False)
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
    # 6. РАБОТА
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="работа", description="💼 Отработать смену и получить зарплату в монетах")
    async def cmd_work(self, inter: disnake.ApplicationCommandInteraction):
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        u_data = await db.get_user(u_uid) or {}

        now = int(time.time())
        last = u_data.get("last_work_ts", 0)
        cd = 3600
        if now - last < cd:
            left = cd - (now - last)
            return await inter.response.send_message(
                f"⏳ Вы уже отработали смену! Отдохните ещё **{left // 60} мин. {left % 60} сек.**",
                ephemeral=True
            )

        salary = random.randint(150, 600)
        jobs = [
            ("Программистом MOXXI Core", "💻 Написали крутой алгоритм для бота"),
            ("Официантом в кибер-баре", "☕️ Разнесли заказы гостям без пролитого кофе"),
            ("Шахтёром в глубоких катакомбах", "⛏ Добыли редкую партию руды"),
            ("Крипто-трейдером", "📈 Успешно закрыли лонг на фьючерсах"),
            ("Курьером экспресс-доставки", "🛵 Доставили все посылки вовремя"),
            ("Охранником в хранилище банка", "🛡 Предотвратили попытку взлома"),
        ]
        job_title, job_desc = random.choice(jobs)

        await db.add_balance(u_uid, salary)
        await db.update_user_action_cooldown(u_uid, "last_work_ts", now)

        embed = disnake.Embed(
            title=f"💼 Трудовая смена: {job_title}",
            description=f"{job_desc}\n\n💰 **Заработано:** `+{salary:,}` 🌑 монет!\n💵 *Деньги зачислены на ваш баланс.*",
            color=disnake.Color.green()
        )
        await inter.response.send_message(embed=embed)

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
    @commands.slash_command(name="магазин", description="🛒 Магазин предметов, сейфов и бустеров опыта")
    async def cmd_shop(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(
            title="🛒 МАГАЗИН ПРЕДМЕТОВ MOXXI",
            description=(
                "Выберите номер товара и купите его через `/купить [номер]`:\n\n"
                "**1.** 🛡 **Сейф от грабителей** — `5,000` 🌑\n"
                "   *100% иммунитет от любых ограблений на 7 дней!*\n\n"
                "**2.** ⚡️ **Бустер опыта 2x** — `2,500` 🌑\n"
                "   *Удваивает весь получаемый XP в чате на 24 часа!*\n\n"
                "**3.** 🎫 **Лотерейный билет** — `500` 🌑\n"
                "   *Шанс выиграть джекпот в ежедневном тираже!*\n\n"
                "**4.** ⛏ **Набор шахтёра** — `1,500` 🌑\n"
                "   *Увеличивает добычу руды в шахте на 50%!*"
            ),
            color=disnake.Color.blurple()
        )
        await inter.response.send_message(embed=embed)

    # ═══════════════════════════════════════════════════════════════
    # 10. КУПИТЬ ПРЕДМЕТ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="купить", description="💳 Купить предмет из магазина по номеру (1-4)")
    async def cmd_buy(
        self,
        inter: disnake.ApplicationCommandInteraction,
        номер_товара: int = commands.Param(ge=1, le=4, description="Номер товара от 1 до 4")
    ):
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        u_data = await db.get_user(u_uid) or {}
        bal = u_data.get("balance", 0)
        now = int(time.time())

        if номер_товара == 1:
            price = 5000
            if bal < price:
                return await inter.response.send_message(f"❌ Недостаточно средств! Нужно `{price:,}` 🌑.", ephemeral=True)
            await db.add_balance(u_uid, -price)
            until = max(now, u_data.get("safe_until", 0)) + 7 * 86400
            await db.set_user_safe(u_uid, until)
            return await inter.response.send_message(f"🛡 Вы успешно приобрели **Сейф от грабителей** на 7 дней (до <t:{until}:F>)!")

        elif номер_товара == 2:
            price = 2500
            if bal < price:
                return await inter.response.send_message(f"❌ Недостаточно средств! Нужно `{price:,}` 🌑.", ephemeral=True)
            await db.add_balance(u_uid, -price)
            until = max(now, u_data.get("xp_booster_until", 0)) + 86400
            await db.set_user_xp_booster(u_uid, until)
            return await inter.response.send_message(f"⚡️ Вы успешно активировали **Бустер опыта 2x** на 24 часа (до <t:{until}:F>)!")

        elif номер_товара == 3:
            price = 500
            if bal < price:
                return await inter.response.send_message(f"❌ Недостаточно средств! Нужно `{price:,}` 🌑.", ephemeral=True)
            await db.add_balance(u_uid, -price)
            return await inter.response.send_message("🎫 Вы купили **Лотерейный билет**! Удачи в розыгрыше!")

        elif номер_товара == 4:
            price = 1500
            if bal < price:
                return await inter.response.send_message(f"❌ Недостаточно средств! Нужно `{price:,}` 🌑.", ephemeral=True)
            await db.add_balance(u_uid, -price)
            return await inter.response.send_message("⛏ Вы приобрели **Набор шахтёра**! Добыча в шахте увеличена!")

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
