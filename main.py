import asyncio
import logging
import os
import sys
import random
import disnake
from disnake.ext import commands

import config
import db
import extended
import commands_catalog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (MOXXI-DC) %(message)s"
)
log = logging.getLogger("moxxi-dc")

intents = disnake.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(*config.PREFIXES),
    intents=intents,
    case_insensitive=True,
    help_command=None
)

# ═══════════════════════════════════════════════════════════════
# 🎨 ИНТЕРАКТИВНЫЕ КНОПКИ DISCORD
# ═══════════════════════════════════════════════════════════════

class MainMenuView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Профиль", emoji="👑", style=disnake.ButtonStyle.success, custom_id="moxxi_dc_profile")
    async def btn_profile(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        db_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(db_uid, username=str(inter.author), first_name=inter.author.display_name)
        u_data = await db.get_user(db_uid) or {}
        embed = disnake.Embed(
            title=f"👑 Профиль игрока {inter.author.display_name}",
            color=disnake.Color.from_rgb(0, 230, 118)
        )
        embed.set_thumbnail(url=inter.author.display_avatar.url)
        embed.add_field(name="💰 На руках", value=f"`{u_data.get('balance', 0):,}` 🌑", inline=True)
        embed.add_field(name="🏦 В банке", value=f"`{u_data.get('bank', 0):,}` 🌑", inline=True)
        embed.add_field(name="🎖 Ранг", value=f"`{u_data.get('rank', 1)} ур.`", inline=True)
        embed.add_field(name="⭐ Опыт / Уровень", value=f"`{u_data.get('level', 1)} ур. ({u_data.get('xp', 0)} XP)`", inline=True)
        await inter.response.send_message(embed=embed, ephemeral=True)

    @disnake.ui.button(label="Бонус", emoji="🎁", style=disnake.ButtonStyle.success, custom_id="moxxi_dc_bonus")
    async def btn_bonus(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        import time
        now = int(time.time())
        db_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(db_uid, username=str(inter.author), first_name=inter.author.display_name)
        u_data = await db.get_user(db_uid) or {}
        last = u_data.get("last_bonus_time", 0) or 0
        if now - last < 86400:
            left = 86400 - (now - last)
            h = left // 3600
            m = (left % 3600) // 60
            await inter.response.send_message(f"⏳ Вы уже забирали бонус! Приходите через **{h} ч {m} мин**.", ephemeral=True)
            return

        reward = random.randint(2500, 7500)
        await db.add_balance(db_uid, reward)
        await db.add_xp(db_uid, 50)
        await db.update_user(db_uid, last_bonus_time=now)
        embed = disnake.Embed(
            title="🎁 Ежедневный бонус получен!",
            description=f"Вам начислено: **+{reward:,} 🌑 монет** и **+50 XP**!",
            color=disnake.Color.gold()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)

    @disnake.ui.button(label="Казино", emoji="🎰", style=disnake.ButtonStyle.danger, custom_id="moxxi_dc_casino")
    async def btn_casino(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_message("🎰 Чтобы сыграть в слоты, напишите в чат: `!казино [ставка]` (например: `!казино 500`)", ephemeral=True)

    @disnake.ui.button(label="Шахта", emoji="⛏", style=disnake.ButtonStyle.primary, custom_id="moxxi_dc_mine")
    async def btn_mine(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        db_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(db_uid, username=str(inter.author), first_name=inter.author.display_name)
        earned = random.randint(200, 800)
        await db.add_balance(db_uid, earned)
        await db.add_xp(db_uid, 15)
        embed = disnake.Embed(
            title="⛏ Добыча ресурсов в шахте",
            description=f"Вы нашли самоцветы и руду на **+{earned:,} 🌑 монет**! (+15 XP)",
            color=disnake.Color.blue()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)

    @disnake.ui.button(label="Все 414 команд", emoji="📖", style=disnake.ButtonStyle.primary, custom_id="moxxi_dc_cmds")
    async def btn_cmds(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_message(commands_catalog.get_hub_text(), ephemeral=True)


# ═══════════════════════════════════════════════════════════════
# 🚀 СОБЫТИЯ DISCORD
# ═══════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    log.info("Бот MOXXI Discord успешно вошел как: %s (ID: %d)", bot.user, bot.user.id)
    await bot.change_presence(
        activity=disnake.Activity(
            type=disnake.ActivityType.playing,
            name="MOXXI 3.0 | !команды • 414+ команд"
        )
    )

@bot.event
async def on_message(message: disnake.Message):
    if message.author.bot:
        return

    clean_txt = message.content.strip()
    if not clean_txt:
        return

    # Убираем префикс если есть
    for pfx in config.PREFIXES:
        if clean_txt.startswith(pfx):
            clean_txt = clean_txt[len(pfx):].strip()
            break

    parts = clean_txt.split()
    if not parts:
        return
    cmd = parts[0].lower()
    args = clean_txt[len(parts[0]):].strip()

    db_uid = config.DISCORD_UID_OFFSET + message.author.id
    await db.ensure_user(db_uid, username=str(message.author), first_name=message.author.display_name)
    u_data = await db.get_user(db_uid) or {}

    # 0. ПРИГЛАШЕНИЕ / ИНВАЙТ НА СЕРВЕР
    if cmd in ("пригласить", "инвайт", "invite", "добавить", "ссылка"):
        invite_url = "https://discord.com/api/oauth2/authorize?client_id=1568910980002619402&permissions=8&scope=bot%20applications.commands"
        view = disnake.ui.View()
        view.add_item(disnake.ui.Button(
            label="➕ Добавить MOXXI на свой сервер",
            url=invite_url,
            style=disnake.ButtonStyle.link,
            emoji="🤖"
        ))
        embed = disnake.Embed(
            title="✨ ПРИГЛАСИТЬ MOXXI 3.0 НА СВОЙ СЕРВЕР ✨",
            description=(
                "👑 **MOXXI** — мощнейший многофункциональный игровой бот!\n\n"
                "🔥 **Что внутри:**\n"
                "• 🏰 Кланы, битвы за территории и общак\n"
                "• 🐉 Рейдовые боссы беседы на 50 000 HP\n"
                "• 🏢 40 уровней бизнеса и пассивный доход\n"
                "• 🎰 Казино, слоты, 21, краш и рулетка\n"
                "• 💘 Семьи, браки, дети и шипперинг (пара дня)\n"
                "• 🛡 Модерация, автокик, варны, муты и ранги 1–10\n"
                "• 📖 Свыше 414 команд!\n\n"
                "👇 **Нажмите кнопку ниже, чтобы добавить бота:**"
            ),
            color=disnake.Color.from_rgb(155, 89, 182)
        )
        if bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        embed.set_footer(text="MOXXI 3.0 Ultimate Edition")
        await message.channel.send(embed=embed, view=view)
        return

    # 1. СТАРТ / ПОМОЩЬ / МЕНЮ
    if cmd in ("старт", "start", "начать", "меню", "help", "помощь", "команды"):
        embed = disnake.Embed(
            title="✨ Добро пожаловать в MOXXI 3.0 (Discord Edition)! ✨",
            description=(
                f"👋 Привет, {message.author.mention}! Я универсальный игровой бот.\n\n"
                f"💰 **Баланс:** `{u_data.get('balance', 0):,}` 🌑 монет\n"
                f"🎖 **Ранг:** `{u_data.get('rank', 1)} ур.` | **Уровень:** `{u_data.get('level', 1)}`\n\n"
                f"🎮 **Быстрые команды:**\n"
                f"• `!профиль` — карточка персонажа\n"
                f"• `!бонус` — забрать ежедневные монеты\n"
                f"• `!банк` — депозиты под 5%\n"
                f"• `!бизнесы` — покупка предприятий\n"
                f"• `!шахта` — копать ресурсы\n"
                f"• `!казино [ставка]` — слоты и азарт\n"
                f"• `!команды` — 12 разделов и 414+ команд!"
            ),
            color=disnake.Color.from_rgb(155, 89, 182)
        )
        if bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        embed.set_footer(text="Нажимайте на кнопки ниже для быстрого действия!")
        await message.channel.send(embed=embed, view=MainMenuView())
        return

    # 2. ПРОФИЛЬ
    elif cmd in ("профиль", "проф", "я", "стата", "баланс"):
        embed = disnake.Embed(
            title=f"👑 Профиль игрока {message.author.display_name}",
            color=disnake.Color.from_rgb(0, 230, 118)
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.add_field(name="💰 На руках", value=f"`{u_data.get('balance', 0):,}` 🌑", inline=True)
        embed.add_field(name="🏦 В банке", value=f"`{u_data.get('bank', 0):,}` 🌑", inline=True)
        embed.add_field(name="🎖 Ранг", value=f"`{u_data.get('rank', 1)} ур.`", inline=True)
        embed.add_field(name="⭐ Опыт / Уровень", value=f"`{u_data.get('level', 1)} ур. ({u_data.get('xp', 0)} XP)`", inline=True)
        await message.channel.send(embed=embed, view=MainMenuView())
        return

    # 3. БОНУС
    elif cmd in ("бонус", "bonus", "ежедневный"):
        import time
        now = int(time.time())
        last = u_data.get("last_bonus_time", 0) or 0
        if now - last < 86400:
            left = 86400 - (now - last)
            h = left // 3600
            m = (left % 3600) // 60
            await message.reply(f"⏳ Вы уже забирали бонус! Приходите через **{h} ч {m} мин**.")
            return

        reward = random.randint(2500, 7500)
        await db.add_balance(db_uid, reward)
        await db.add_xp(db_uid, 50)
        await db.update_user(db_uid, last_bonus_time=now)
        embed = disnake.Embed(
            title="🎁 Ежедневный бонус получен!",
            description=f"Вам начислено: **+{reward:,} 🌑 монет** и **+50 XP**!",
            color=disnake.Color.gold()
        )
        await message.reply(embed=embed)
        return

    # 4. ШАХТА
    elif cmd in ("шахта", "копать"):
        earned = random.randint(200, 800)
        await db.add_balance(db_uid, earned)
        await db.add_xp(db_uid, 15)
        embed = disnake.Embed(
            title="⛏ Добыча ресурсов в шахте",
            description=f"Вы нашли самоцветы и руду на **+{earned:,} 🌑 монет**! (+15 XP)",
            color=disnake.Color.blue()
        )
        await message.reply(embed=embed)
        return

    # 5. КАЗИНО
    elif cmd in ("казино", "слоты", "кз"):
        if not args:
            await message.reply("🎰 Чтобы сыграть, напишите: `!казино [ставка]` (например: `!казино 500`)")
            return
        try:
            bet = int(args.split()[0])
        except ValueError:
            await message.reply("❌ Укажите ставку числом, например: `!казино 500`")
            return

        bal = u_data.get("balance", 0)
        if bet <= 0 or bet > bal:
            await message.reply(f"❌ Недостаточно монет! Ваш баланс: `{bal:,}` 🌑")
            return

        symbols = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]
        s1 = random.choice(symbols)
        s2 = random.choice(symbols)
        s3 = random.choice(symbols)

        if s1 == s2 == s3:
            mult = 7 if s1 == "7️⃣" else (5 if s1 == "💎" else 3)
            win = bet * mult
            await db.add_balance(db_uid, win - bet)
            embed = disnake.Embed(
                title="🎰 ИГРОВОЙ АВТОМАТ MOXXI",
                description=f"**[ {s1} | {s2} | {s3} ]**\n\n🎉 **ДЖЕКПОТ!** Вы выиграли **x{mult} (+{win:,} 🌑)**!",
                color=disnake.Color.green()
            )
        else:
            await db.add_balance(db_uid, -bet)
            embed = disnake.Embed(
                title="🎰 ИГРОВОЙ АВТОМАТ MOXXI",
                description=f"**[ {s1} | {s2} | {s3} ]**\n\n💔 **Не повезло!** Вы проиграли **{bet:,} 🌑**.",
                color=disnake.Color.red()
            )
        await message.reply(embed=embed)
        return

async def main():
    token = config.DISCORD_BOT_TOKEN
    if not token or token == "YOUR_TOKEN_HERE":
        log.warning("DISCORD_BOT_TOKEN не задан в config.py!")
        return

    await db.init()
    log.info("Запуск Discord бота MOXXI...")
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
