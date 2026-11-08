"""🎮 MOXXI 3.0 ULTIMATE DISCORD EDITION
Папка: C:\\Users\\eiema\\OneDrive\\Desktop\\moxxidc

Премиальный Discord-бот с интерактивным интерфейсом:
1. 🃏 Интерактивный Блэкджек (21 Очко) с реальными кнопками Hit, Stand, Double
2. ⚔️ PvP Дуэли между участниками сервера с кнопками вызова
3. 🐉 Рейдовый Босс сервера с живой шкалой здоровья и кнопкой удара
4. 🏢 Империя Предприятий (40 видов бизнеса, сбор прибыли)
5. 🏦 Государственный Банк: вклады под 5% в сутки и снятие
6. 🎰 Казино, Слоты, Краш, Кости
7. 💍 Свадьбы, Браки и Семьи
8. ⛏ Шахта и Рыбалка с редкими ресурсами
9. 🥷 Ограбления игроков с риском полиции и штрафов
10. 🏆 Топ богачей сервера с медалями 🥇🥈🥉
11. 📦 Кейсы и Лутбоксы
12. 🎮 Прямой запуск Mini App (Web App)
13. 📖 Интерактивное меню помощи со всеми 12 категориями и 414 командами
"""
from __future__ import annotations

import asyncio
import aiohttp
import datetime
import html
import json
import logging
import os
import random
import re
import sys
import time

import disnake
from disnake.ext import commands

import config
import db
import extended
import commands_catalog
import wordle_game

# UTF-8 в консоли
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (MOXXI-DC) %(message)s"
)
log = logging.getLogger("moxxi-dc")

intents = disnake.Intents.default()
intents.message_content = True
intents.members = False

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(*config.PREFIXES),
    intents=intents,
    case_insensitive=True,
    help_command=None,
    test_guilds=[848248778384474124],
    sync_commands_debug=True,
)
bot.load_extension("slash_suite")

INVITE_URL = "https://discord.com/api/oauth2/authorize?client_id=1568910980002619402&permissions=8&scope=bot%20applications.commands"
WEBAPP_URL = "https://gaskimka-oss.github.io/MOXXI/"

# ═══════════════════════════════════════════════════════════════
# 🃏 КАРТОЧНЫЙ ДВИЖОК ДЛЯ БЛЭКДЖЕКА (21 ОЧКО)
# ═══════════════════════════════════════════════════════════════
SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

def draw_card():
    return random.choice(RANKS), random.choice(SUITS)

def card_str(c):
    return f"`{c[0]}{c[1]}`"

def hand_value(cards):
    val = 0
    aces = 0
    for r, _ in cards:
        if r in ("J", "Q", "K"):
            val += 10
        elif r == "A":
            aces += 1
            val += 11
        else:
            val += int(r)
    while val > 21 and aces > 0:
        val -= 10
        aces -= 1
    return val

class BlackjackView(disnake.ui.View):
    def __init__(self, author_id: int, bet: int, db_uid: int, player_cards: list, dealer_cards: list):
        super().__init__(timeout=90.0)
        self.author_id = author_id
        self.bet = bet
        self.db_uid = db_uid
        self.player_cards = player_cards
        self.dealer_cards = dealer_cards
        self.is_finished = False

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.author_id:
            await inter.response.send_message("❌ Это не ваша игра!", ephemeral=True)
            return False
        return True

    def build_embed(self, finished: bool = False, outcome: str = ""):
        p_val = hand_value(self.player_cards)
        p_str = " ".join([card_str(c) for c in self.player_cards])
        if finished:
            d_val = hand_value(self.dealer_cards)
            d_str = " ".join([card_str(c) for c in self.dealer_cards])
        else:
            d_str = f"{card_str(self.dealer_cards[0])} `🂠`"
            d_val = "?"

        color = disnake.Color.gold()
        if finished:
            if "выиграли" in outcome.lower() or "победа" in outcome.lower() or "джекпот" in outcome.lower():
                color = disnake.Color.from_rgb(46, 204, 113)
            elif "проиграли" in outcome.lower() or "перебор" in outcome.lower():
                color = disnake.Color.from_rgb(231, 76, 60)

        embed = disnake.Embed(
            title="🃏 БЛЭКДЖЕК (21 ОЧКО) · MOXXI CASINO",
            color=color
        )
        embed.add_field(name=f"Ваша рука ({p_val} очков)", value=p_str, inline=False)
        embed.add_field(name=f"Рука дилера ({d_val} очков)", value=d_str, inline=False)
        embed.add_field(name="💰 Ставка", value=f"`{self.bet:,}` 🌑", inline=True)
        if outcome:
            embed.add_field(name="🏁 Результат", value=outcome, inline=False)
        return embed

    @disnake.ui.button(label="Ещё (Hit)", emoji="🃏", style=disnake.ButtonStyle.success)
    async def btn_hit(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if self.is_finished:
            return
        self.player_cards.append(draw_card())
        p_val = hand_value(self.player_cards)
        if p_val > 21:
            self.is_finished = True
            for b in self.children:
                b.disabled = True
            await db.add_balance(self.db_uid, -self.bet)
            embed = self.build_embed(finished=True, outcome=f"💥 **Перебор ({p_val} очк.)!** Вы проиграли **{self.bet:,} 🌑**.")
            await inter.response.edit_message(embed=embed, view=self)
            return
        elif p_val == 21:
            await self.finish_game(inter)
            return
        await inter.response.edit_message(embed=self.build_embed(), view=self)

    @disnake.ui.button(label="Хватит (Stand)", emoji="🛑", style=disnake.ButtonStyle.danger)
    async def btn_stand(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if self.is_finished:
            return
        await self.finish_game(inter)

    @disnake.ui.button(label="Удвоить (Double)", emoji="⚡", style=disnake.ButtonStyle.primary)
    async def btn_double(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if self.is_finished:
            return
        u_data = await db.get_user(self.db_uid) or {}
        bal = u_data.get("balance", 0)
        if bal < self.bet * 2:
            await inter.response.send_message("❌ Недостаточно монет для удвоения ставки!", ephemeral=True)
            return
        self.bet *= 2
        self.player_cards.append(draw_card())
        await self.finish_game(inter)

    async def finish_game(self, inter: disnake.MessageInteraction):
        self.is_finished = True
        for b in self.children:
            b.disabled = True
        p_val = hand_value(self.player_cards)
        if p_val > 21:
            await db.add_balance(self.db_uid, -self.bet)
            embed = self.build_embed(finished=True, outcome=f"💥 **Перебор ({p_val} очк.)!** Вы проиграли **{self.bet:,} 🌑**.")
            await inter.response.edit_message(embed=embed, view=self)
            return

        while hand_value(self.dealer_cards) < 17:
            self.dealer_cards.append(draw_card())

        d_val = hand_value(self.dealer_cards)
        if d_val > 21:
            await db.add_balance(self.db_uid, self.bet)
            embed = self.build_embed(finished=True, outcome=f"🎉 **Дилер перебрал ({d_val} очк.)!** Вы выиграли **+{self.bet:,} 🌑**!")
        elif p_val > d_val:
            await db.add_balance(self.db_uid, self.bet)
            embed = self.build_embed(finished=True, outcome=f"🎉 **Победа!** ({p_val} против {d_val}) Вы выиграли **+{self.bet:,} 🌑**!")
        elif p_val < d_val:
            await db.add_balance(self.db_uid, -self.bet)
            embed = self.build_embed(finished=True, outcome=f"💔 **Дилер победил!** ({d_val} против {p_val}) Вы проиграли **{self.bet:,} 🌑**.")
        else:
            embed = self.build_embed(finished=True, outcome=f"🤝 **Ничья ({p_val} очк.)!** Ставка возвращена.")
        await inter.response.edit_message(embed=embed, view=self)


# ═══════════════════════════════════════════════════════════════
# ⚔️ ИНТЕРАКТИВНЫЕ ДУЭЛИ МЕЖДУ ИГРОКАМИ
# ═══════════════════════════════════════════════════════════════
class DuelChallengeView(disnake.ui.View):
    def __init__(self, challenger: disnake.Member, opponent: disnake.Member, bet: int):
        super().__init__(timeout=90.0)
        self.challenger = challenger
        self.opponent = opponent
        self.bet = bet
        self.challenger_uid = config.DISCORD_UID_OFFSET + challenger.id
        self.opponent_uid = config.DISCORD_UID_OFFSET + opponent.id

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.opponent.id:
            await inter.response.send_message(f"❌ Этот вызов адресован {self.opponent.mention}!", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="Принять вызов", emoji="⚔️", style=disnake.ButtonStyle.success)
    async def btn_accept(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        for b in self.children:
            b.disabled = True
        c_bal = (await db.get_user(self.challenger_uid) or {}).get("balance", 0)
        o_bal = (await db.get_user(self.opponent_uid) or {}).get("balance", 0)
        if c_bal < self.bet or o_bal < self.bet:
            await inter.response.edit_message(content="❌ У одного из участников недостаточно монет для дуэли!", embed=None, view=None)
            return

        c_roll = random.randint(1, 100)
        o_roll = random.randint(1, 100)
        while c_roll == o_roll:
            o_roll = random.randint(1, 100)

        if c_roll > o_roll:
            winner = self.challenger
            loser = self.opponent
            w_uid, l_uid = self.challenger_uid, self.opponent_uid
        else:
            winner = self.opponent
            loser = self.challenger
            w_uid, l_uid = self.opponent_uid, self.challenger_uid

        await db.add_balance(w_uid, self.bet)
        await db.add_balance(l_uid, -self.bet)
        await db.add_xp(w_uid, 35)

        embed = disnake.Embed(
            title="⚔️ PvP ДУЭЛЬ MOXXI ЗАВЕРШЕНА! ⚔️",
            description=(
                f"🎲 **Броски костей судьбы:**\n"
                f"• {self.challenger.mention}: **{c_roll}** очков\n"
                f"• {self.opponent.mention}: **{o_roll}** очков\n\n"
                f"🏆 **Победитель:** {winner.mention} (**+{self.bet:,} 🌑**)!\n"
                f"💔 **Проигравший:** {loser.mention} (**-{self.bet:,} 🌑**)."
            ),
            color=disnake.Color.gold()
        )
        await inter.response.edit_message(embed=embed, view=None)

    @disnake.ui.button(label="Отклонить", emoji="🏳️", style=disnake.ButtonStyle.danger)
    async def btn_decline(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        for b in self.children:
            b.disabled = True
        await inter.response.edit_message(content=f"🏳️ {self.opponent.mention} отклонил(а) дуэль от {self.challenger.mention}.", embed=None, view=None)


# ═══════════════════════════════════════════════════════════════
# 🐉 РЕЙДОВЫЙ БОСС СЕРВЕРА С КНОПКОЙ УДАРА
# ═══════════════════════════════════════════════════════════════
class BossRaidView(disnake.ui.View):
    def __init__(self, db_cid: int):
        super().__init__(timeout=None)
        self.db_cid = db_cid
        self.cooldowns = {}

    @disnake.ui.button(label="Нанести удар", emoji="⚔️", style=disnake.ButtonStyle.danger, custom_id="moxxi_dc_boss_hit")
    async def btn_hit(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        now = time.time()
        last = self.cooldowns.get(inter.author.id, 0)
        if now - last < 8.0:
            left = int(8.0 - (now - last))
            await inter.response.send_message(f"⏳ Перезарядка оружия! Подождите **{left} сек.**", ephemeral=True)
            return

        self.cooldowns[inter.author.id] = now
        db_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(db_uid, username=str(inter.author), first_name=inter.author.display_name)

        dmg = random.randint(350, 1500)
        res = await db.attack_chat_boss(self.db_cid, db_uid, dmg)

        if res.get("killed"):
            rew = res.get("reward", 50000)
            await db.add_balance(db_uid, rew)
            embed = disnake.Embed(
                title="💥 БОСС СЕРВЕРА ПОВЕРЖЕН! 💥",
                description=f"🎉 {inter.author.mention} нанёс смертельный удар на **{dmg} урона** и забрал казну босса: **+{rew:,} 🌑 монет**!",
                color=disnake.Color.gold()
            )
            await inter.response.edit_message(embed=embed, view=None)
            return

        left_hp = res.get("hp_left", 0)
        max_hp = res.get("max_hp", 50000)
        percent = max(0, min(100, int((left_hp / max_hp) * 100)))
        bar = "█" * (percent // 10) + "░" * (10 - (percent // 10))

        embed = disnake.Embed(
            title="🐉 РЕЙДОВЫЙ БОСС СЕРВЕРА",
            description=(
                f"⚔️ {inter.author.mention} нанёс **{dmg:,} урона** боссу!\n\n"
                f"❤️ Здоровье: `[{bar}]` **{percent}%** ({left_hp:,} / {max_hp:,} HP)\n\n"
                f"Бейте босса всей гильдией, чтобы поделить казну!"
            ),
            color=disnake.Color.red()
        )
        await inter.response.edit_message(embed=embed, view=self)


# ═══════════════════════════════════════════════════════════════
# 💍 СВАДЕБНОЕ ПРЕДЛОЖЕНИЕ
# ═══════════════════════════════════════════════════════════
class MarriageProposalView(disnake.ui.View):
    def __init__(self, proposer: disnake.Member, target: disnake.Member):
        super().__init__(timeout=90.0)
        self.proposer = proposer
        self.target = target

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.target.id:
            await inter.response.send_message(f"❌ Предложение сделано для {self.target.mention}!", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="Я согласен(на)!", emoji="💍", style=disnake.ButtonStyle.success)
    async def btn_accept(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        p_uid = config.DISCORD_UID_OFFSET + self.proposer.id
        t_uid = config.DISCORD_UID_OFFSET + self.target.id
        await db.create_marriage(p_uid, t_uid)
        embed = disnake.Embed(
            title="💖 ГОРЬКО! НОВАЯ СЕМЬЯ В MOXXI! 💖",
            description=f"🎉 {self.proposer.mention} и {self.target.mention} теперь официально муж и жена!\nЛюбви, гармонии и процветания молодой семье!",
            color=disnake.Color.from_rgb(255, 105, 180)
        )
        await inter.response.edit_message(embed=embed, view=None)

    @disnake.ui.button(label="Отказать", emoji="💔", style=disnake.ButtonStyle.danger)
    async def btn_decline(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        embed = disnake.Embed(
            title="💔 ОТКАЗ В ПРЕДЛОЖЕНИИ",
            description=f"{self.target.mention} отклонил(а) предложение руки и сердца от {self.proposer.mention}.",
            color=disnake.Color.dark_grey()
        )
        await inter.response.edit_message(embed=embed, view=None)


# ═══════════════════════════════════════════════════════════════
# 📖 ИНТЕРАКТИВНОЕ МЕНЮ ПОМОЩИ (SELECT DROPDOWN)
# ═══════════════════════════════════════════════════════════════
class HelpSelect(disnake.ui.StringSelect):
    def __init__(self):
        options = [
            disnake.SelectOption(label="Администрация и Ранги", value="sec_1", emoji="👑", description="Ранги 1-10, варны, муты, бан, кик"),
            disnake.SelectOption(label="Экономика и Банк", value="sec_2", emoji="💰", description="Баланс, депозиты 5%, переводы"),
            disnake.SelectOption(label="Бизнесы и Недвижимость", value="sec_3", emoji="🏢", description="40 предприятий, сбор пассивной прибыли"),
            disnake.SelectOption(label="Казино и Азартные игры", value="sec_4", emoji="🎰", description="21 Очко, Слоты, Краш, Рулетка, Кости"),
            disnake.SelectOption(label="PvP Дуэли и Битвы", value="sec_5", emoji="⚔️", description="Дуэли на монеты, вызовы игроков"),
            disnake.SelectOption(label="Рейдовые Боссы", value="sec_6", emoji="🐉", description="Рейдовые боссы беседы на 50 000 HP"),
            disnake.SelectOption(label="Кланы и Банды", value="sec_7", emoji="🏰", description="Создание клана, казна, битвы"),
            disnake.SelectOption(label="Семьи, Браки и Дети", value="sec_8", emoji="💍", description="Свадьба, развод, завести ребенка"),
            disnake.SelectOption(label="Шахта и Рыбалка", value="sec_9", emoji="⛏", description="Фарм руды, самоцветов и редкой рыбы"),
            disnake.SelectOption(label="Автопарк и Гараж", value="sec_10", emoji="🚗", description="Покупка авто от Vesta до Bugatti"),
            disnake.SelectOption(label="Кейсы и Лутбоксы", value="sec_11", emoji="🎁", description="4 уровня кейсов, дроп суперкаров"),
            disnake.SelectOption(label="РП Реакции и Действия", value="sec_12", emoji="🎭", description="Обнять, поцеловать, погладить, кусь"),
        ]
        super().__init__(
            placeholder="Выберите раздел команд...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="moxxi_dc_help_select"
        )

    async def callback(self, inter: disnake.MessageInteraction):
        val = self.values[0]
        sec_num = int(val.split("_")[1])
        text = commands_catalog.get_section_text(sec_num)

        embed = disnake.Embed(
            title=f"📖 Раздел #{sec_num} · MOXXI Каталог Команд",
            description=text,
            color=disnake.Color.from_rgb(155, 89, 182)
        )
        embed.set_footer(text="MOXXI 3.0 Ultimate • Выберите другой раздел в меню ниже")
        await inter.response.edit_message(embed=embed, view=self.view)

class HelpView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HelpSelect())
        self.add_item(disnake.ui.Button(label="🎮 Играть в WebApp", url=WEBAPP_URL, style=disnake.ButtonStyle.link, emoji="🕹"))
        self.add_item(disnake.ui.Button(label="➕ Пригласить бота", url=INVITE_URL, style=disnake.ButtonStyle.link, emoji="🤖"))


# ═══════════════════════════════════════════════════════════════
# 🎨 ГЛАВНОЕ МЕНЮ С БЫСТРЫМИ КНОПКАМИ
# ═══════════════════════════════════════════════════════════════
class MainMenuView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(disnake.ui.Button(label="🎮 Играть в WebApp", url=WEBAPP_URL, style=disnake.ButtonStyle.link, emoji="🕹"))
        self.add_item(disnake.ui.Button(label="➕ Добавить на сервер", url=INVITE_URL, style=disnake.ButtonStyle.link, emoji="🤖"))

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
        embed.add_field(name="⭐ Опыт / Уровень", value=f"**Уровень {max(1, int((u_data.get('xp', 0) / 100) ** 0.5) + 1)}** • `{u_data.get('xp', 0):,} XP`", inline=True)
        await inter.response.send_message(embed=embed, ephemeral=True)

    @disnake.ui.button(label="Бонус", emoji="🎁", style=disnake.ButtonStyle.success, custom_id="moxxi_dc_bonus")
    async def btn_bonus(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
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
        await inter.response.send_message("🎰 Чтобы сыграть в слоты, напишите в чат: `!казино [ставка]` или `!21 [ставка]` для блэкджека!", ephemeral=True)

    @disnake.ui.button(label="Шахта", emoji="⛏", style=disnake.ButtonStyle.primary, custom_id="moxxi_dc_mine")
    async def btn_mine(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        db_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(db_uid, username=str(inter.author), first_name=inter.author.display_name)
        earned = random.randint(250, 950)
        await db.add_balance(db_uid, earned)
        await db.add_xp(db_uid, 20)
        embed = disnake.Embed(
            title="⛏ Добыча ресурсов в шахте",
            description=f"Вы нашли драгоценные самоцветы на **+{earned:,} 🌑 монет**! (+20 XP)",
            color=disnake.Color.blue()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)

    @disnake.ui.button(label="Все 414 команд", emoji="📖", style=disnake.ButtonStyle.secondary, custom_id="moxxi_dc_cmds")
    async def btn_cmds(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        embed = disnake.Embed(
            title="📖 БАЗА ЗНАНИЙ MOXXI 3.0",
            description=commands_catalog.get_hub_text(),
            color=disnake.Color.from_rgb(155, 89, 182)
        )
        await inter.response.send_message(embed=embed, view=HelpView(), ephemeral=True)


async def keep_alive_pulse():
    """Фоновый пульс для пробуждения Windows IOCP цикла и предотвращения задержек WebSocket"""
    while True:
        await asyncio.sleep(1.0)

# ═══════════════════════════════════════════════════════════════
# 🚀 СОБЫТИЯ DISCORD
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# 👑 СИСТЕМА РАНГОВ (1-10) И ИНТЕГРАЦИЯ ПРАВ DISCORD
# ═══════════════════════════════════════════════════════════════
RANK_NAMES = {
    0: "Участник",
    1: "Стажёр",
    2: "Младший модератор",
    3: "Старший модератор",
    4: "Главный модератор",
    5: "Младший админ",
    6: "Старший админ",
    7: "Главный админ",
    8: "Тех. администратор",
    9: "Заместитель",
    10: "Владелец чата",
}

RANK_ICONS = {
    0: "👤",
    1: "🌱",
    2: "🔹",
    3: "🔷",
    4: "🌟",
    5: "⚡️",
    6: "🔮",
    7: "💎",
    8: "⚙️",
    9: "🛡",
    10: "👑",
}

RANK_PROMOTIONS = {
    "+владелец": 10, "+лидер": 10, "+создатель": 10,
    "+зам": 9, "+заместитель": 9,
    "+техадмин": 8, "+тех админ": 8, "+технический администратор": 8,
    "+га": 7, "+главный админ": 7, "+главный администратор": 7,
    "+са": 6, "+старший админ": 6, "+старший администратор": 6,
    "+ма": 5, "+младший админ": 5, "+младший администратор": 5,
    "+гм": 4, "+гл": 4, "+главный модер": 4, "+главный модератор": 4,
    "+см": 3, "+старший модер": 3, "+старший модератор": 3,
    "+мм": 2, "+младший модер": 2, "+младший модератор": 2,
    "+стажер": 1, "+стажёр": 1,
}

RANK_DEMOTIONS = {
    "-владелец", "-лидер", "-создатель",
    "-зам", "-заместитель",
    "-техадмин", "-тех админ", "-технический администратор",
    "-га", "-главный админ", "-главный администратор",
    "-са", "-старший админ", "-старший администратор",
    "-ма", "-младший админ", "-младший администратор",
    "-гм", "-гл", "-главный модер", "-главный модератор",
    "-см", "-старший модер", "-старший модератор",
    "-мм", "-младший модер", "-младший модератор",
    "-стажер", "-стажёр",
}

TWO_WORD_CMDS = {
    "мой ранг", "мой_ранг", "топ уровень", "топ лвл", "топ дамаг", "топ урон",
    "+главный админ", "+старший админ", "+младший админ",
    "+главный модер", "+старший модер", "+младший модер",
    "+главный модератор", "+старший модератор", "+младший модератор",
    "+тех админ", "+технический администратор",
    "-главный админ", "-старший админ", "-младший админ",
    "-главный модер", "-старший модер", "-младший модер",
    "-главный модератор", "-старший модератор", "-младший модератор",
    "-тех админ", "-технический администратор",
    "купить бизнес", "снять варн", "взять тикет", "закрыть тикет",
    "панель тикетов", "панель верификации", "сервер инфо", "юзер инфо",
    "привязать ник", "пинг сервера"
}

KNOWN_COMMANDS = {
    # 0. Инвайт и веб
    "пригласить", "инвайт", "invite", "добавить", "ссылка",
    "играть", "апп", "app", "веб", "игра",
    # 1. Меню и помощь
    "старт", "start", "начать", "меню", "help", "помощь", "команды", "каталог",
    # 2. Профиль и экономика
    "профиль", "проф", "я", "стата", "баланс", "profile", "balance",
    "бонус", "bonus", "ежедневный",
    "банк", "депозит",
    "бизнес", "бизнесы", "предприятия", "прибыль", "собрать", "купить_бизнес", "купитьбиз", "купить бизнес",
    "шахта", "копать", "рыбалка", "ловить",
    "ограбить", "кража", "rob",
    "топ", "богачи", "лидеры", "top",
    "брак", "свадьба", "пожениться", "развод",
    "передать", "дать", "pay",
    # 3. Игры и казино
    "21", "очко", "bj", "blackjack",
    "дуэль", "битвы", "fight", "duel",
    "босс", "рейд", "boss",
    "казино", "слоты", "рулетка",
    # 4. Ранги и состав
    "ранг", "мой ранг", "мой_ранг", "мойранг", "rank",
    "состав", "стафф", "админы", "модераторы", "staff", "admins", "сетка",
    "повысить", "+ранг", "ранг+", "up",
    "понизить", "-ранг", "ранг-", "down",
    "назначить", "setrank",
    "снять", "разжаловать", "демоут",
    # 5. Модерация
    "кик", "kick", "бан", "ban", "варн", "warn", "варны", "warns",
    "снятьварн", "снять варн", "unwarn", "мут", "mute", "размут", "unmute",
    # 6. Поддержка и тикеты
    "поддержка", "тикет", "support", "ticket", "панель_тикетов", "панель тикетов", "вордл", "wordle",
    # 7. МОДУЛЬ MINECRAFT
    "сервер", "пинг", "mc", "скин", "skin", "голова", "head",
    "привязать_ник", "привязать ник", "ник_мс", "панель_верификации", "панель верификации", "верификация",
    # 8. МОДУЛЬ РОЗЫГРЫШЕЙ
    "розыгрыш", "giveaway", "конкурс",
    # 9. МОДУЛЬ УРОВНЕЙ И XP
    "уровень", "лвл", "топ_уровень", "топ_лвл", "топ уровень", "топ лвл", "levels",
    # 10. МОДУЛЬ МОДЕРАЦИИ И АУДИТА
    "очистить", "clear", "purge", "сервер_инфо", "сервер инфо", "юзер_инфо", "юзер инфо",
    # 11. МОДУЛЬ ЭКОНОМИКИ И КАРЬЕРЫ
    "работа", "работать", "work", "смена", "работы", "вакансии", "профессии", "устроиться", "уволиться",
    "попрошайничать", "бомжевать", "beg",
    "криминал", "crime",
    "магазин", "шоп", "shop", "купить",
    "инвентарь", "инв", "inv", "рюкзак",
}
KNOWN_COMMANDS.update(RANK_PROMOTIONS.keys())
KNOWN_COMMANDS.update(RANK_DEMOTIONS)


def get_discord_native_rank(member: disnake.Member) -> int:
    """Определяет автоматический ранг в боте по нативным правам роли в Discord"""
    if not isinstance(member, disnake.Member) or not member.guild:
        return 0
    # Владелец сервера Discord
    if member.guild.owner_id == member.id:
        return 10
    perms = member.guild_permissions
    if perms.administrator:
        return 9
    if perms.manage_guild:
        return 8
    if perms.ban_members and perms.manage_roles:
        return 7
    if perms.ban_members or perms.kick_members:
        return 6
    if perms.manage_messages and perms.moderate_members:
        return 5
    if perms.manage_messages:
        return 3
    if perms.moderate_members:
        return 2
    return 0


async def get_effective_rank(guild_id: int, member: disnake.Member | disnake.User) -> int:
    """Возвращает максимальный ранг: нативный Discord или выданный в БД бота"""
    native = get_discord_native_rank(member) if isinstance(member, disnake.Member) else 0
    db_cid = config.DISCORD_UID_OFFSET + guild_id
    db_uid = config.DISCORD_UID_OFFSET + member.id
    db_r = await db.get_user_rank(db_cid, db_uid)
    return max(native, db_r)


async def extract_target_discord_member(message: disnake.Message, args: str) -> disnake.Member | disnake.User | None:
    """Находит целевого пользователя: по упоминанию, по ответу на сообщение или по ID"""
    for m in message.mentions:
        if m.id != bot.user.id:
            return m
    if message.reference and message.reference.message_id:
        try:
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
            if ref_msg and ref_msg.author and ref_msg.author.id != bot.user.id:
                if message.guild:
                    gm = message.guild.get_member(ref_msg.author.id)
                    if gm:
                        return gm
                return ref_msg.author
        except Exception:
            pass
    id_m = re.search(r"\b(\d{17,20})\b", args)
    if id_m:
        uid = int(id_m.group(1))
        if message.guild:
            gm = message.guild.get_member(uid)
            if gm:
                return gm
        try:
            return await bot.fetch_user(uid)
        except Exception:
            pass
    return None


def detect_staff_abuse(text: str) -> tuple[bool, str]:
    """Проверка ответа сотрудника поддержки на мат и оскорбления игроков"""
    t = text.lower()
    subs = {'@': 'а', 'a': 'а', 'm': 'м', 't': 'т', 'b': 'б', '0': 'о', 'o': 'о', 'e': 'е'}
    norm = "".join(subs.get(c, c) for c in t)

    parent_patterns = [
        r'\b(мать|матери|матерью|мамаша|мамашу|мамка|мамку|мамке|мамок|мамки|мку|mq)\b',
        r'(твой|твою|твоя|твоей|твоем)\s+(мать|мамк|мамаш)',
        r'(сын|дочь|отродье)\s+(шлюхи|бляди|собаки)',
    ]
    for pat in parent_patterns:
        if re.search(pat, norm):
            return True, "Упоминание/оскорбление родных"

    insult_patterns = [
        r'\b(шлюх|блядин|уебищ|уёбищ|хуесос|пидорас|пидар|гандон|мразь|тварь)\w*',
        r'(пошел|пошёл|иди)\s+на\s*хуй',
        r'\b(долбоеб|долбоёб|даун|ублюдок)\b',
    ]
    for pat in insult_patterns:
        if re.search(pat, norm):
            return True, "Нецензурная брань / оскорбление игрока"

    return False, ""


# ═══════════════════════════════════════════════════════════════
# 🆘 СИСТЕМА ТИКЕТОВ И ПОДДЕРЖКИ С КНОПКАМИ И АНТИ-АФК
# ═══════════════════════════════════════════════════════════════
class TicketAnswerModal(disnake.ui.Modal):
    def __init__(self, ticket_id: int, ticket: dict):
        self.ticket_id = ticket_id
        self.ticket = ticket
        components = [
            disnake.ui.TextInput(
                label=f"Ответ на тикет #{ticket_id}",
                placeholder="Введите текст решения проблемы для игрока...",
                custom_id="ticket_ans_text",
                style=disnake.TextInputStyle.paragraph,
                min_length=3,
                max_length=1500,
            )
        ]
        super().__init__(title=f"Ответ на тикет #{ticket_id}", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        ans = inter.text_values.get("ticket_ans_text", "").strip()
        is_abuse, abuse_reason = detect_staff_abuse(ans)
        if is_abuse:
            return await inter.response.send_message(
                f"⛔️ **Ответ заблокирован ИИ-супервайзером!**\nОбнаружено нарушение: *{abuse_reason}*.\nСоблюдайте правила общения!",
                ephemeral=True
            )
        await db.answer_support_ticket(self.ticket_id, inter.author.id, inter.author.display_name, ans)

        # Отправляем ответ игроку в ЛС
        raw_uid = self.ticket.get("user_id", 0)
        u_discord_id = raw_uid - config.DISCORD_UID_OFFSET if raw_uid >= config.DISCORD_UID_OFFSET else raw_uid
        try:
            target_user = await bot.fetch_user(u_discord_id)
            if target_user:
                u_embed = disnake.Embed(
                    title=f"📩 Ответ от техподдержки MOXXI (Тикет #{self.ticket_id})",
                    description=(
                        f"📝 **Ваше обращение:**\n*{self.ticket.get('text', '')}*\n\n"
                        f"👨‍💻 **Ответ администрации ({inter.author.display_name}):**\n"
                        f"{ans}\n\n"
                        f"🔒 *Тикет успешно закрыт. Если возникнет новый вопрос: `тикет [вопрос]`*"
                    ),
                    color=disnake.Color.green()
                )
                await target_user.send(embed=u_embed)
        except Exception as e:
            log.warning("Не удалось отправить ЛС автору тикета: %s", e)

        if inter.message:
            try:
                cl_embed = inter.message.embeds[0] if inter.message.embeds else disnake.Embed(title=f"Тикет #{self.ticket_id}")
                cl_embed.color = disnake.Color.green()
                cl_embed.add_field(name="✅ Закрыт", value=f"Ответил: {inter.author.mention}", inline=False)
                await inter.message.edit(embed=cl_embed, view=None)
            except Exception:
                pass
        await inter.response.send_message(f"✅ Ответ по тикету #{self.ticket_id} успешно доставлен пользователю!", ephemeral=True)


class DiscordTicketView(disnake.ui.View):
    def __init__(self, ticket_id: int, claimed_by: int = 0, claimed_name: str = ""):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        self.claimed_by = claimed_by
        self.claimed_name = claimed_name
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()
        if not self.claimed_by:
            self.add_item(disnake.ui.Button(
                label="💬 Взять в работу / Ответить",
                style=disnake.ButtonStyle.success,
                custom_id=f"dc_t_claim:{self.ticket_id}",
                emoji="✋"
            ))
            self.add_item(disnake.ui.Button(
                label="⛔️ Быстрый отказ",
                style=disnake.ButtonStyle.danger,
                custom_id=f"dc_t_reject:{self.ticket_id}",
                emoji="🚫"
            ))
        else:
            self.add_item(disnake.ui.Button(
                label=f"🔒 Занят: {self.claimed_name}",
                style=disnake.ButtonStyle.secondary,
                custom_id=f"dc_t_busy:{self.ticket_id}",
                disabled=True
            ))
            self.add_item(disnake.ui.Button(
                label="✍️ Ответить игроку",
                style=disnake.ButtonStyle.primary,
                custom_id=f"dc_t_answer:{self.ticket_id}",
                emoji="📩"
            ))
            self.add_item(disnake.ui.Button(
                label="🔄 Сложная ситуация / Освободить",
                style=disnake.ButtonStyle.secondary,
                custom_id=f"dc_t_release:{self.ticket_id}",
                emoji="↩️"
            ))
            self.add_item(disnake.ui.Button(
                label="⛔️ Отказать",
                style=disnake.ButtonStyle.danger,
                custom_id=f"dc_t_reject:{self.ticket_id}",
                emoji="🚫"
            ))



_user_xp_cd: dict[int, float] = {}

def build_progress_bar(cur: int, total: int, length: int = 10) -> str:
    ratio = min(1.0, max(0.0, cur / total if total > 0 else 0))
    filled = int(length * ratio)
    return "▰" * filled + "▱" * (length - filled)

async def giveaway_watcher():
    """Фоновый мониторинг розыгрышей: автоматическое подведение итогов по таймеру"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            active_gws = await db.get_active_giveaways()
            for gw in active_gws:
                gw_id = gw["id"]
                cid = gw["channel_id"]
                mid = gw["message_id"]
                prize = gw["prize"]
                w_count = gw["winners_count"]
                entries = json.loads(gw.get("entries_json") or "[]")

                channel = bot.get_channel(cid)
                if not channel:
                    try:
                        channel = await bot.fetch_channel(cid)
                    except Exception:
                        channel = None

                await db.finish_giveaway(gw_id)

                if not entries:
                    res_desc = f"❌ В розыгрыше **{prize}** никто не принял участие!"
                    if channel:
                        try:
                            msg = await channel.fetch_message(mid)
                            embed = msg.embeds[0] if msg.embeds else disnake.Embed(title="🎉 РОЗЫГРЫШ ЗАВЕРШЁН")
                            embed.color = disnake.Color.red()
                            embed.description = res_desc
                            await msg.edit(embed=embed, view=None)
                        except Exception:
                            pass
                    continue

                winners_count = min(len(entries), w_count)
                winners_uids = random.sample(entries, winners_count)
                winners_mentions = [f"<@{uid}>" for uid in winners_uids]

                # Проверяем начисление монет
                num_m = re.search(r"\b(\d+)\b", prize.replace(" ", ""))
                if num_m and "монет" in prize.lower():
                    coins_win = int(num_m.group(1))
                    for w_uid in winners_uids:
                        t_db_uid = config.DISCORD_UID_OFFSET + w_uid
                        await db.add_balance(t_db_uid, coins_win)

                win_str = ", ".join(winners_mentions)
                res_desc = (
                    f"🏆 **ПОЗДРАВЛЯЕМ ПОБЕДИТЕЛЕЙ!**\n\n"
                    f"🎁 **Приз:** {prize}\n"
                    f"👑 **Победители:** {win_str}\n\n"
                    f"📊 *Всего участников:* `{len(entries)}`"
                )

                if channel:
                    try:
                        msg = await channel.fetch_message(mid)
                        embed = msg.embeds[0] if msg.embeds else disnake.Embed(title="🎉 РОЗЫГРЫШ ЗАВЕРШЁН")
                        embed.color = disnake.Color.gold()
                        embed.description = res_desc
                        await msg.edit(embed=embed, view=None)
                        await channel.send(f"🎉 Розыгрыш **{prize}** завершён! Победители: {win_str}!")
                    except Exception as e:
                        log.warning("giveaway update message error: %s", e)
        except Exception as e:
            log.warning("giveaway_watcher error: %s", e)
        await asyncio.sleep(10.0)

async def anti_afk_ticket_watcher():
    """Фоновый страж: если тикет занят стаффом более 1 часа без ответа, возвращает в общий пул"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            stale_tickets = await db.get_stale_claimed_tickets(timeout_sec=3600)
            for t in stale_tickets:
                tid = t["id"]
                c_name = t.get("claimed_name") or "Сотрудник"
                await db.release_support_ticket(tid)
                log.info("Тикет #%d возвращён в общий пул (1 час анти-АФК таймаут стаффа %s)", tid, c_name)
        except Exception as e:
            log.warning("anti_afk_ticket_watcher error: %s", e)
        await asyncio.sleep(60.0)

@bot.event
async def on_ready():
    log.info("Бот MOXXI Discord успешно вошел как: %s (ID: %d)", bot.user, bot.user.id)
    try:
        await bot._sync_application_commands()
        log.info("Слэш-команды успешно синхронизированы с Discord!")
    except Exception as e:
        log.warning("Ошибка синхронизации команд: %s", e)
    bot.add_view(MainMenuView())
    bot.add_view(HelpView())
    asyncio.create_task(keep_alive_pulse())
    asyncio.create_task(anti_afk_ticket_watcher())
    asyncio.create_task(giveaway_watcher())
    await bot.change_presence(
        activity=disnake.Activity(
            type=disnake.ActivityType.playing,
            name="MOXXI 3.0 | команды • 414+ команд"
        )
    )

@bot.event
async def on_message(message: disnake.Message):
    if message.author.bot:
        return

    clean_txt = message.content.strip()
    if not clean_txt:
        return

    # Опциональное снятие префикса (!, m!, ., /) если пользователь его написал
    for pfx in ("!", "m!", ".", "/"):
        if clean_txt.startswith(pfx):
            clean_txt = clean_txt[len(pfx):].strip()
            break

    if bot.user.mentioned_in(message):
        clean_txt = clean_txt.replace(bot.user.mention, "").strip()

    parts = clean_txt.split()
    if not parts:
        return

    raw_first = parts[0].lower()
    raw_two = f"{parts[0]} {parts[1]}".lower() if len(parts) >= 2 else ""

    if raw_two in TWO_WORD_CMDS:
        cmd = raw_two
        args = clean_txt[len(parts[0]) + 1 + len(parts[1]):].strip()
    else:
        cmd = raw_first
        args = clean_txt[len(parts[0]):].strip()

    # Если сообщение не является зарегистрированной командой бота — игнорируем
    if cmd not in KNOWN_COMMANDS:
        return

    db_uid = config.DISCORD_UID_OFFSET + message.author.id
    db_cid = config.DISCORD_UID_OFFSET + (message.guild.id if message.guild else message.channel.id)

    await db.ensure_user(db_uid, username=str(message.author), first_name=message.author.display_name)
    u_data = await db.get_user(db_uid) or {}

    # Начисление XP за активность в чате
    now_ts = time.time()
    if now_ts - _user_xp_cd.get(message.author.id, 0) >= 45.0:
        _user_xp_cd[message.author.id] = now_ts
        xp_gain = random.randint(15, 25)
        new_xp, new_lvl, leveled_up = await db.add_user_xp(db_uid, xp_gain)
        if leveled_up:
            lvl_reward = new_lvl * 1500
            await db.add_balance(db_uid, lvl_reward)
            try:
                await message.channel.send(
                    f"🎉 {message.author.mention}, уровень повышен до **[{new_lvl} ур.]**! 💰 Награда: `+{lvl_reward:,}` 🌑 монет!"
                )
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════
    # 0. ИНВАЙТ / ПРИГЛАШЕНИЕ
    # ═══════════════════════════════════════════════════════════
    if cmd in ("пригласить", "инвайт", "invite", "добавить", "ссылка"):
        view = disnake.ui.View()
        view.add_item(disnake.ui.Button(label="➕ Добавить MOXXI на свой сервер", url=INVITE_URL, style=disnake.ButtonStyle.link, emoji="🤖"))
        view.add_item(disnake.ui.Button(label="🎮 Открыть WebApp", url=WEBAPP_URL, style=disnake.ButtonStyle.link, emoji="🕹"))
        embed = disnake.Embed(
            title="✨ ПРИГЛАСИТЬ MOXXI НА СВОЙ СЕРВЕР ✨",
            description=(
                "👑 **MOXXI** — мощнейший многофункциональный игровой бот!\n\n"
                "🔥 **Что внутри:**\n"
                "• 🃏 Полноценный Блэкджек (21) с кнопками Hit/Stand\n"
                "• ⚔️ PvP Дуэли между игроками\n"
                "• 🐉 Рейдовые боссы беседы на 50 000 HP\n"
                "• 🏢 40 уровней бизнеса и пассивный доход\n"
                "• 🎰 Казино, слоты, краш и рулетка\n"
                "• 💘 Семьи, браки, дети и шипперинг\n"
                "• 🛡 Модерация, ранги 1–10\n"
                "• 📖 Свыше 414 команд!\n\n"
                "👇 Нажмите кнопку ниже для добавления:"
            ),
            color=disnake.Color.from_rgb(155, 89, 182)
        )
        if bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        await message.channel.send(embed=embed, view=view)
        return

    # ═══════════════════════════════════════════════════════════
    # 1. СТАРТ / ПОМОЩЬ / МЕНЮ
    # ═══════════════════════════════════════════════════════════
    if cmd in ("старт", "start", "начать", "меню", "help", "помощь", "команды", "каталог"):
        embed = disnake.Embed(
            title="✨ Добро пожаловать в MOXXI 3.0 (Discord Edition)! ✨",
            description=(
                f"👋 Привет, {message.author.mention}! Я универсальный игровой бот.\n\n"
                f"💰 **Баланс:** `{u_data.get('balance', 0):,}` 🌑 монет\n"
                f"🎖 **Ранг:** `{u_data.get('rank', 1)} ур.` | **Уровень:** `{u_data.get('level', 1)}`\n\n"
                f"🎮 **Быстрые команды:**\n"
                f"• `!21 [ставка]` — интерактивный блэкджек с кнопками\n"
                f"• `!дуэль @user [ставка]` — вызвать игрока на битву\n"
                f"• `!босс` — рейдовый босс сервера с полоской HP\n"
                f"• `!бизнесы` — покупка предприятий и пассивный доход\n"
                f"• `!банк` — депозиты под 5% в сутки\n"
                f"• `!шахта` / `!рыбалка` — копать ресурсы\n"
                f"• `!топ` — богачи сервера\n"
                f"• `!брак @user` — сделать предложение\n"
                f"• `!команды` — полный справочник из 414 команд!"
            ),
            color=disnake.Color.from_rgb(155, 89, 182)
        )
        if bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        await message.channel.send(embed=embed, view=HelpView())
        return

    # ═══════════════════════════════════════════════════════════
    # 2. ПРОФИЛЬ
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("профиль", "проф", "я", "стата", "баланс"):
        embed = disnake.Embed(
            title=f"👑 Профиль игрока {message.author.display_name}",
            color=disnake.Color.from_rgb(0, 230, 118)
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.add_field(name="💰 На руках", value=f"`{u_data.get('balance', 0):,}` 🌑", inline=True)
        embed.add_field(name="🏦 В банке", value=f"`{u_data.get('bank', 0):,}` 🌑", inline=True)
        embed.add_field(name="🎖 Ранг", value=f"`{u_data.get('rank', 1)} ур.`", inline=True)
        embed.add_field(name="⭐ Опыт / Уровень", value=f"**Уровень {max(1, int((u_data.get('xp', 0) / 100) ** 0.5) + 1)}** • `{u_data.get('xp', 0):,} XP`", inline=True)
        await message.channel.send(embed=embed, view=MainMenuView())
        return

    # ═══════════════════════════════════════════════════════════
    # 3. БОНУС
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("бонус", "bonus", "ежедневный"):
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

    # ═══════════════════════════════════════════════════════════
    # 4. БЛЭКДЖЕК (21 ОЧКО) С КНОПКАМИ
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("21", "блэкджек", "bj", "blackjack"):
        if not args:
            await message.reply("🃏 Чтобы сыграть, укажите ставку: `!21 [ставка]` (например: `!21 500`)")
            return
        try:
            bet = int(args.split()[0])
        except ValueError:
            await message.reply("❌ Укажите ставку числом, например: `!21 500`")
            return

        bal = u_data.get("balance", 0)
        if bet <= 0 or bet > bal:
            await message.reply(f"❌ Недостаточно средств! Ваш баланс: `{bal:,}` 🌑")
            return

        p_cards = [draw_card(), draw_card()]
        d_cards = [draw_card(), draw_card()]

        view = BlackjackView(message.author.id, bet, db_uid, p_cards, d_cards)
        embed = view.build_embed()
        await message.reply(embed=embed, view=view)
        return

    # ═══════════════════════════════════════════════════════════
    # 5. PvP ДУЭЛЬ С КНОПКАМИ
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("дуэль", "бой", "fight", "duel"):
        if not message.mentions:
            await message.reply("⚔️ Укажите соперника через @упоминание и ставку! Пример: `!дуэль @User 1000`")
            return
        opponent = message.mentions[0]
        if opponent.id == message.author.id:
            await message.reply("❌ Нельзя вызвать самого себя на дуэль!")
            return
        if opponent.bot:
            await message.reply("❌ Нельзя вызывать ботов на дуэль!")
            return

        bet = 100
        p_nums = re.findall(r"\b\d+\b", args)
        if p_nums:
            bet = int(p_nums[0])

        bal = u_data.get("balance", 0)
        if bet <= 0 or bet > bal:
            await message.reply(f"❌ У вас недостаточно монет для ставки `{bet:,}` 🌑!")
            return

        o_uid = config.DISCORD_UID_OFFSET + opponent.id
        await db.ensure_user(o_uid, username=str(opponent), first_name=opponent.display_name)
        o_bal = (await db.get_user(o_uid) or {}).get("balance", 0)
        if o_bal < bet:
            await message.reply(f"❌ У {opponent.mention} недостаточно монет для дуэли (нужно `{bet:,}` 🌑)!")
            return

        view = DuelChallengeView(message.author, opponent, bet)
        embed = disnake.Embed(
            title="⚔️ ВЫЗОВ НА PvP ДУЭЛЬ! ⚔️",
            description=(
                f"🔥 {message.author.mention} бросает вызов {opponent.mention}!\n\n"
                f"💰 **Ставка кона:** `{bet:,}` 🌑 монет с каждого\n"
                f"Победитель забирает весь банк: **+{bet * 2:,} 🌑**!\n\n"
                f"👉 {opponent.mention}, нажми кнопку ниже:"
            ),
            color=disnake.Color.red()
        )
        await message.channel.send(content=f"{opponent.mention}", embed=embed, view=view)
        return

    # ═══════════════════════════════════════════════════════════
    # 6. РЕЙДОВЫЙ БОСС СЕРВЕРА
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("босс", "рейд", "boss"):
        boss = await db.get_chat_boss(db_cid)
        if not boss:
            await db.conn().execute(
                "INSERT INTO chat_bosses (chat_id, name, hp, max_hp, reward, spawned_at) VALUES (?, ?, ?, ?, ?, ?)",
                (db_cid, "Древний Кибер-Дракон", 50000, 50000, 100000, int(time.time()))
            )
            await db.conn().commit()
            boss = await db.get_chat_boss(db_cid)

        hp = boss.get("hp", 0)
        max_hp = boss.get("max_hp", 50000)
        percent = max(0, min(100, int((hp / max_hp) * 100)))
        bar = "█" * (percent // 10) + "░" * (10 - (percent // 10))

        embed = disnake.Embed(
            title="🐉 РЕЙДОВЫЙ БОСС СЕРВЕРА 🐉",
            description=(
                f"👹 **Имя:** `{boss.get('name', 'Древний Кибер-Дракон')}`\n"
                f"❤️ **Здоровье:** `[{bar}]` **{percent}%** ({hp:,} / {max_hp:,} HP)\n"
                f"💰 **Награда за победу:** `{boss.get('reward', 100000):,}` 🌑\n\n"
                f"⚔️ Нажмите кнопку ниже, чтобы нанести удар по боссу!"
            ),
            color=disnake.Color.red()
        )
        view = BossRaidView(db_cid)
        await message.channel.send(embed=embed, view=view)
        return

    # ═══════════════════════════════════════════════════════════
    # 7. СЛОТЫ / КАЗИНО
    # ═══════════════════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════════════════
    # 8. БАНК И ВКЛАДЫ
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("банк", "депозит"):
        sub = args.lower().strip()
        bank_val = u_data.get("bank", 0)
        bal_val = u_data.get("balance", 0)

        if sub.startswith("положить"):
            parts = sub.split()
            amount_str = parts[1] if len(parts) > 1 else ""
            amt = bal_val if amount_str in ("все", "всё") else (int(amount_str) if amount_str.isdigit() else 0)
            if amt <= 0 or amt > bal_val:
                await message.reply(f"❌ Недостаточно средств на руках! У вас: `{bal_val:,}` 🌑.")
                return
            await db.deposit_to_bank(db_uid, amt)
            await message.reply(f"🏦 Вы успешно положили в банк `{amt:,}` 🌑! В банке: `{bank_val + amt:,}` 🌑.")
            return

        elif sub.startswith("снять"):
            parts = sub.split()
            amount_str = parts[1] if len(parts) > 1 else ""
            amt = bank_val if amount_str in ("все", "всё") else (int(amount_str) if amount_str.isdigit() else 0)
            if amt <= 0 or amt > bank_val:
                await message.reply(f"❌ Недостаточно средств в банке! В банке: `{bank_val:,}` 🌑.")
                return
            await db.withdraw_from_bank(db_uid, amt)
            await message.reply(f"🏦 Вы успешно сняли из банка `{amt:,}` 🌑! На руках: `{bal_val + amt:,}` 🌑.")
            return

        embed = disnake.Embed(
            title="🏦 ГОСУДАРСТВЕННЫЙ БАНК MOXXI",
            description=(
                f"💳 **Ваш депозит:** `{bank_val:,}` 🌑 монет\n"
                f"💰 **На руках:** `{bal_val:,}` 🌑 монет\n"
                f"📈 **Процентная ставка:** `+5%` каждые 24 часа\n\n"
                f"💡 **Команды:**\n"
                f"• `!банк положить [сумма/все]` — сделать вклад\n"
                f"• `!банк снять [сумма/все]` — забрать средства"
            ),
            color=disnake.Color.blue()
        )
        await message.reply(embed=embed)
        return

    # ═══════════════════════════════════════════════════════════
    # 9. БИЗНЕСЫ И ПАССИВНЫЙ ДОХОД
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("бизнесы", "бизнес", "предприятия", "прибыль"):
        if cmd == "прибыль" or args.lower().strip() in ("собрать", "прибыль", "доход"):
            profit = await db.collect_business_profit(db_uid)
            if profit > 0:
                await message.reply(f"💰 Вы собрали накопившуюся прибыль с предприятий: **+{profit:,} 🌑**!")
            else:
                await message.reply("Прибыль ещё не накопилась (начисления производятся каждый час).")
            return

        u_biz = await db.get_user_businesses(db_uid)
        user_level = max(1, u_data.get("xp", 0) // 100)

        embed = disnake.Embed(
            title="🏢 ИМПЕРИЯ ПРЕДПРИЯТИЙ MOXXI 🏢",
            description=f"👤 **Владелец:** {message.author.mention} (`{user_level} Lvl`)\n",
            color=disnake.Color.from_rgb(241, 196, 15)
        )

        if u_biz:
            total_inc = 0
            b_list = []
            for b in u_biz:
                k = b["biz_key"]
                real_k = db.BIZ_ALIASES.get(k, k)
                if real_k in db.BIZ_CATALOG:
                    b_info = db.BIZ_CATALOG[real_k]
                    inc = b_info["daily_income"] * b["count"]
                    total_inc += inc
                    b_list.append(f"• **{b_info['name']}** (x{b['count']}) ➔ `+{inc:,} 🌑/день`")
            embed.add_field(name="💼 Ваши предприятия:", value="\n".join(b_list), inline=False)
            embed.add_field(name="📈 Суммарный доход:", value=f"`+{total_inc:,} 🌑/день`", inline=False)

        cat_lines = []
        for idx, (k, info) in enumerate(list(db.BIZ_CATALOG.items())[:8]):
            status = "✅" if user_level >= info["req_lvl"] else f"🔒 Lvl {info['req_lvl']}"
            cat_lines.append(f"`{idx+1}.` **{info['name']}** — `{info['cost']:,}` 🌑 (+`{info['daily_income']:,}`/д | {status})")

        embed.add_field(name="📦 Каталог для покупки:", value="\n".join(cat_lines), inline=False)
        embed.set_footer(text="Купить: !купить_бизнес [1-40] • Собрать доход: !прибыль")
        await message.reply(embed=embed)
        return

    elif cmd in ("купить_бизнес", "купитьбизнес"):
        keys = list(db.BIZ_CATALOG.keys())
        idx_match = re.search(r"\b(\d+)\b", args)
        b_key = None
        if idx_match:
            idx_val = int(idx_match.group(1))
            if 1 <= idx_val <= len(keys):
                b_key = keys[idx_val - 1]

        if not b_key or b_key not in db.BIZ_CATALOG:
            await message.reply("❌ Укажите номер предприятия от 1 до 40! Пример: `!купить_бизнес 1` (Каталог: `!бизнесы`).")
            return

        b_info = db.BIZ_CATALOG[b_key]
        user_bal = u_data.get("balance", 0)
        user_lvl = max(1, u_data.get("xp", 0) // 100)

        if user_lvl < b_info["req_lvl"]:
            await message.reply(f"🔒 Для покупки «{b_info['name']}» требуется **{b_info['req_lvl']} уровень**!")
            return

        if user_bal < b_info["cost"]:
            await message.reply(f"❌ Недостаточно монет! Стоимость: `{b_info['cost']:,}` 🌑, у вас: `{user_bal:,}` 🌑.")
            return

        await db.add_balance(db_uid, -b_info["cost"])
        await db.buy_business(db_uid, b_key)
        await db.add_xp(db_uid, 30)
        await message.reply(f"🎉 Поздравляем! Вы приобрели предприятие **«{b_info['name']}»**! Доход: `+{b_info['daily_income']:,} 🌑/день`.")
        return

    # ═══════════════════════════════════════════════════════════
    # 10. ШАХТА И РЫБАЛКА
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("шахта", "копать"):
        earned = random.randint(250, 950)
        await db.add_balance(db_uid, earned)
        await db.add_xp(db_uid, 20)
        embed = disnake.Embed(
            title="⛏ Добыча полезных ископаемых",
            description=f"Вы нашли алмазы и редкую руду на **+{earned:,} 🌑 монет**! (+20 XP)",
            color=disnake.Color.blue()
        )
        await message.reply(embed=embed)
        return

    elif cmd in ("рыбалка", "рыбачить"):
        earned = random.randint(300, 1100)
        await db.add_balance(db_uid, earned)
        await db.add_xp(db_uid, 25)
        fish = random.choice(["Золотой Осетр", "Неоновый Карп", "Глубоководный Угорь", "Таймень", "Атлантический Лосось"])
        embed = disnake.Embed(
            title="🎣 Улов на озере",
            description=f"Вы выловили редкую рыбу **«{fish}»** и сдали её за **+{earned:,} 🌑 монет**! (+25 XP)",
            color=disnake.Color.teal()
        )
        await message.reply(embed=embed)
        return

    # ═══════════════════════════════════════════════════════════
    # 11. ОГРАБЛЕНИЕ ИГРОКОВ (CRIME)
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("ограбить", "украсть", "rob"):
        if not message.mentions:
            await message.reply("🥷 Укажите жертву через @упоминание: `!ограбить @User`")
            return
        target = message.mentions[0]
        if target.id == message.author.id:
            await message.reply("❌ Нельзя ограбить самого себя!")
            return
        if target.bot:
            await message.reply("❌ Нельзя грабить ботов!")
            return

        t_uid = config.DISCORD_UID_OFFSET + target.id
        t_data = await db.get_user(t_uid) or {}
        t_bal = t_data.get("balance", 0)

        if t_bal < 500:
            await message.reply(f"❌ У {target.mention} в карманах пусто (меньше 500 🌑)!")
            return

        success = random.random() < 0.45
        if success:
            stolen = int(t_bal * random.uniform(0.05, 0.18))
            stolen = max(100, stolen)
            await db.add_balance(t_uid, -stolen)
            await db.add_balance(db_uid, stolen)
            embed = disnake.Embed(
                title="🥷 УСПЕШНОЕ ОГРАБЛЕНИЕ!",
                description=f"Вы бесшумно подкрались и украли у {target.mention} **{stolen:,} 🌑 монет**!",
                color=disnake.Color.green()
            )
        else:
            fine = random.randint(300, 1500)
            await db.add_balance(db_uid, -fine)
            embed = disnake.Embed(
                title="🚨 ПОЛИЦИЯ НА СВЯЗИ!",
                description=f"Патруль поймал вас за руку при попытке ограбить {target.mention}!\nВыписан штраф: **-{fine:,} 🌑 монет**.",
                color=disnake.Color.red()
            )
        await message.reply(embed=embed)
        return

    # ═══════════════════════════════════════════════════════════
    # 12. ТОП БОГАЧЕЙ
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("топ", "богачи", "лидеры", "top"):
        rows = await db.fetchall("SELECT user_id, first_name, username, balance FROM users ORDER BY balance DESC LIMIT 10")
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        lines = []
        for idx, r in enumerate(rows):
            med = medals[idx] if idx < len(medals) else f"{idx+1}."
            name = r["first_name"] or r["username"] or f"ID {r['user_id']}"
            lines.append(f"{med} **{name}** — `{r['balance']:,}` 🌑")

        embed = disnake.Embed(
            title="🏆 ТОП-10 БОГАЧЕЙ ЭКОСИСТЕМЫ MOXXI 🏆",
            description="\n".join(lines),
            color=disnake.Color.gold()
        )
        embed.set_footer(text="Зарабатывайте в шахте, бизнесе и казино, чтобы подняться выше!")
        await message.reply(embed=embed)
        return

    # ═══════════════════════════════════════════════════════════
    # 13. БРАКИ И СЕМЬИ
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("брак", "жениться", "пожениться", "свадьба"):
        if not message.mentions:
            await message.reply("💍 Укажите свою вторую половинку через @упоминание: `!брак @User`")
            return
        target = message.mentions[0]
        if target.id == message.author.id:
            await message.reply("❌ Нельзя жениться на самом себе!")
            return
        if target.bot:
            await message.reply("❌ Боты не выходят замуж!")
            return

        view = MarriageProposalView(message.author, target)
        embed = disnake.Embed(
            title="💍 ПРЕДЛОЖЕНИЕ РУКИ И СЕРДЦА 💍",
            description=(
                f"💖 {message.author.mention} опускается на одно колено и делает предложение {target.mention}!\n\n"
                f"👉 {target.mention}, вы согласны связать свою судьбу в MOXXI?"
            ),
            color=disnake.Color.from_rgb(255, 105, 180)
        )
        await message.channel.send(content=f"{target.mention}", embed=embed, view=view)
        return

    # ═══════════════════════════════════════════════════════════
    # 14. РП РЕАКЦИИ (ОБНЯТЬ, ПОЦЕЛОВАТЬ И Т.Д.)
    # ═══════════════════════════════════════════════════════════
    rp_actions = {
        "обнять": ("🤗", "крепко обнял(а)"),
        "поцеловать": ("💋", "нежно поцеловал(а)"),
        "погладить": ("👋", "ласково погладил(а) по голове"),
        "кусь": ("🦷", "игриво сделал(а) кусь за ушко"),
        "ударить": ("👊", "отвесил(а) смачную оплеуху"),
        "пнуть": ("🦵", "дал(а) пенделя"),
        "дать_пять": ("✋", "дал(а) пять"),
    }
    if cmd in rp_actions:
        icon, verb = rp_actions[cmd]
        target_name = message.mentions[0].mention if message.mentions else (args if args else "всех вокруг")
        embed = disnake.Embed(
            description=f"{icon} {message.author.mention} **{verb}** {target_name}!",
            color=disnake.Color.from_rgb(230, 126, 34)
        )
        await message.channel.send(embed=embed)
        return

    # ═══════════════════════════════════════════════════════════
    # 15. ПЕРЕДАЧА МОНЕТ ИГРОКУ
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("передать", "дать", "pay"):
        if not message.mentions:
            await message.reply("💸 Укажите получателя через @упоминание и сумму: `!передать @User 1000`")
            return
        target = message.mentions[0]
        if target.id == message.author.id:
            await message.reply("❌ Нельзя переводить монеты самому себе!")
            return
        nums = re.findall(r"\b\d+\b", args)
        if not nums:
            await message.reply("❌ Укажите сумму для перевода!")
            return
        amt = int(nums[0])
        bal = u_data.get("balance", 0)
        if amt <= 0 or amt > bal:
            await message.reply(f"❌ Недостаточно средств! Ваш баланс: `{bal:,}` 🌑.")
            return

        t_uid = config.DISCORD_UID_OFFSET + target.id
        await db.ensure_user(t_uid, username=str(target), first_name=target.display_name)
        await db.add_balance(db_uid, -amt)
        await db.add_balance(t_uid, amt)
        embed = disnake.Embed(
            title="💸 ПЕРЕВОД МОНЕТ",
            description=f"✅ {message.author.mention} успешно перевёл **{amt:,} 🌑 монет** {target.mention}!",
            color=disnake.Color.green()
        )
        await message.reply(embed=embed)
        return

    # ═══════════════════════════════════════════════════════════
    # 16. WEBAPP ИГРА
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("играть", "апп", "app", "веб"):
        view = disnake.ui.View()
        view.add_item(disnake.ui.Button(label="🎮 Запустить MOXXI WebApp", url=WEBAPP_URL, style=disnake.ButtonStyle.link, emoji="🕹"))
        embed = disnake.Embed(
            title="🎮 ИНТЕРАКТИВНОЕ WEB-ПРИЛОЖЕНИЕ MOXXI",
            description="Открывайте полноэкранную игру прямо в браузере или мобильном приложении: кликер, казино, инвентарь и рулетки!",
            color=disnake.Color.from_rgb(0, 242, 254)
        )
        await message.reply(embed=embed, view=view)
        return



    # ═══════════════════════════════════════════════════════════
    # 17. 👑 СИСТЕМА РАНГОВ И СОСТАВ АДМИНИСТРАЦИИ (1–10)
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("ранг", "мой ранг", "мой_ранг", "мойранг", "rank"):
        target = await extract_target_discord_member(message, args) or message.author
        if not message.guild:
            t_rank = u_data.get("rank", 1)
            t_title = RANK_NAMES.get(t_rank, "Участник")
            t_icon = RANK_ICONS.get(t_rank, "👤")
            return await message.reply(f"{t_icon} Ваш глобальный ранг: **[{t_rank}] {t_title}**")

        t_rank = await get_effective_rank(message.guild.id, target)
        t_title = RANK_NAMES.get(t_rank, "Участник")
        t_icon = RANK_ICONS.get(t_rank, "👤")

        native_r = get_discord_native_rank(target) if isinstance(target, disnake.Member) else 0
        if target.id == message.guild.owner_id:
            src = "👑 Владелец сервера Discord"
        elif native_r >= 9:
            src = "🛡 Права Администратора Discord"
        elif native_r > 0:
            src = "⚙️ Права модератора сервера Discord"
        elif t_rank > 0:
            src = "🎖 Назначен администрацией в боте"
        else:
            src = "👤 Обычный участник"

        embed = disnake.Embed(
            title=f"{t_icon} РАНГ УЧАСТНИКА · MOXXI",
            description=(
                f"👤 **Пользователь:** {target.mention}\n"
                f"🎖 **Ступень:** `[{t_rank}/10]` **{t_title}** {t_icon}\n"
                f"📌 **Источник прав:** *{src}*\n\n"
                f"💡 *Справка по рангам: `состав` или `команды`*"
            ),
            color=disnake.Color.from_rgb(155, 89, 182)
        )
        if target.avatar:
            embed.set_thumbnail(url=target.avatar.url)
        await message.reply(embed=embed)
        return

    elif cmd in ("состав", "стафф", "админы", "модераторы", "staff", "admins", "сетка"):
        if not message.guild:
            return await message.reply("❌ Состав администрации доступен только на сервере!")

        staff_by_rank = {r: [] for r in range(10, 0, -1)}
        seen_uids = set()

        # 1. Владелец сервера
        owner_id = message.guild.owner_id
        if owner_id:
            owner_m = message.guild.get_member(owner_id)
            owner_tag = owner_m.mention if owner_m else f"<@{owner_id}>"
            staff_by_rank[10].append(owner_tag)
            seen_uids.add(owner_id)

        # 2. Нативные права в Discord
        for mem in message.guild.members:
            if mem.bot or mem.id in seen_uids:
                continue
            nr = get_discord_native_rank(mem)
            if nr > 0:
                staff_by_rank[nr].append(mem.mention)
                seen_uids.add(mem.id)

        # 3. Назначенные модераторы из базы данных бота
        staff_rows = await db.get_chat_staff_list(db_cid)
        for sr in staff_rows:
            raw_uid = sr["user_id"] - config.DISCORD_UID_OFFSET
            if raw_uid not in seen_uids:
                rnk = sr["rank"]
                if 1 <= rnk <= 10:
                    staff_by_rank[rnk].append(f"<@{raw_uid}>")
                    seen_uids.add(raw_uid)

        embed = disnake.Embed(
            title="👥 СОСТАВ АДМИНИСТРАЦИИ СЕРВЕРА 👥",
            color=disnake.Color.from_rgb(155, 89, 182)
        )
        total_staff = sum(len(v) for v in staff_by_rank.values())
        if total_staff == 0:
            embed.description = "В этом сервере пока нет назначенных модераторов."
        else:
            for r in range(10, 0, -1):
                m_list = staff_by_rank[r]
                if m_list:
                    icon = RANK_ICONS.get(r, "⭐")
                    title = RANK_NAMES.get(r, f"Ранг {r}")
                    embed.add_field(
                        name=f"{icon} [{r}] {title} ({len(m_list)})",
                        value="\n".join([f"• {m}" for m in m_list]),
                        inline=False
                    )
        embed.set_footer(text=f"📊 Всего сотрудников: {total_staff} • Настройка: повысить/понизить/@юзер")
        await message.reply(embed=embed)
        return

    elif cmd in ("повысить", "+ранг", "ранг+", "up"):
        if not message.guild:
            return await message.reply("❌ Команда доступна только на сервере!")
        sender_rank = await get_effective_rank(message.guild.id, message.author)
        if sender_rank < 2:
            return await message.reply("⛔️ Повышать участников могут сотрудники от **[2] Младший модератор**!")

        target = await extract_target_discord_member(message, args)
        if not target or target.id == message.author.id:
            return await message.reply("❌ Укажите пользователя через `@упоминание` или ответом на сообщение!")

        target_rank = await get_effective_rank(message.guild.id, target)
        if sender_rank <= target_rank:
            return await message.reply(f"⛔️ Вы не можете повысить пользователя с рангом `[{target_rank}]`, равным или выше вашего (`[{sender_rank}]`)!")
        if target_rank + 1 >= sender_rank and sender_rank < 10:
            return await message.reply(f"⛔️ Вы не можете повысить пользователя до своего ранга `[{sender_rank}]`!")
        if target_rank >= 10:
            return await message.reply("⚠️ У пользователя уже максимальный ранг (10 - Владелец)!")

        new_rank = target_rank + 1
        t_db_uid = config.DISCORD_UID_OFFSET + target.id
        await db.set_user_rank(db_cid, t_db_uid, new_rank, granted_by=db_uid)
        icon = RANK_ICONS[new_rank]
        title = RANK_NAMES[new_rank]
        await message.reply(f"🎉 **{target.mention}** повышен(а) до ранга **[{new_rank}] {title} {icon}**!\n👨‍💻 Назначил: {message.author.mention}")
        return

    elif cmd in ("понизить", "-ранг", "ранг-", "down"):
        if not message.guild:
            return await message.reply("❌ Команда доступна только на сервере!")
        sender_rank = await get_effective_rank(message.guild.id, message.author)
        if sender_rank < 2:
            return await message.reply("⛔️ Понижать участников могут сотрудники от **[2] Младший модератор**!")

        target = await extract_target_discord_member(message, args)
        if not target or target.id == message.author.id:
            return await message.reply("❌ Укажите пользователя через `@упоминание` или ответом на сообщение!")

        target_rank = await get_effective_rank(message.guild.id, target)
        if sender_rank <= target_rank:
            return await message.reply(f"⛔️ Вы не можете понизить пользователя с рангом `[{target_rank}]`, равным или выше вашего (`[{sender_rank}]`)!")
        if target_rank <= 0:
            return await message.reply("⚠️ У пользователя уже минимальный ранг `[0]` (Участник)!")

        new_rank = target_rank - 1
        t_db_uid = config.DISCORD_UID_OFFSET + target.id
        await db.set_user_rank(db_cid, t_db_uid, new_rank, granted_by=db_uid)
        icon = RANK_ICONS[new_rank]
        title = RANK_NAMES[new_rank]
        await message.reply(f"🔻 **{target.mention}** понижен(а) до ранга **[{new_rank}] {title} {icon}**!\n👨‍💻 Изменил: {message.author.mention}")
        return

    elif cmd in ("назначить", "setrank"):
        if not message.guild:
            return await message.reply("❌ Команда доступна только на сервере!")
        sender_rank = await get_effective_rank(message.guild.id, message.author)
        if sender_rank < 2:
            return await message.reply("⛔️ Назначать ранги могут сотрудники от **[2] Младший модератор**!")

        target = await extract_target_discord_member(message, args)
        if not target or target.id == message.author.id:
            return await message.reply("💡 Формат: `назначить @юзер [1-10]`")

        clean_args = re.sub(r"<@!?\d+>", "", args).strip()
        num_m = re.search(r"\b(\d+)\b", clean_args)
        if not num_m:
            return await message.reply("⚠️ Укажите ступень ранга от 0 до 10! Пример: `назначить @юзер 3`")
        req_rank = int(num_m.group(1))
        if req_rank < 0 or req_rank > 10:
            return await message.reply("⚠️ Номер ранга должен быть от 0 до 10!")

        target_rank = await get_effective_rank(message.guild.id, target)
        if sender_rank <= target_rank:
            return await message.reply(f"⛔️ Вы не можете изменять ранг равного или старшего по должности (`[{target_rank}]`)!")
        if req_rank >= sender_rank and sender_rank < 10:
            return await message.reply(f"⛔️ Вы можете назначать ранги строго ниже своего (максимум `[{sender_rank - 1}]`)!")

        t_db_uid = config.DISCORD_UID_OFFSET + target.id
        await db.set_user_rank(db_cid, t_db_uid, req_rank, granted_by=db_uid)
        icon = RANK_ICONS[req_rank]
        title = RANK_NAMES[req_rank]
        await message.reply(f"✅ Пользователю **{target.mention}** установлен ранг: **[{req_rank}] {title} {icon}**!\n👨‍💻 Назначил: {message.author.mention}")
        return

    elif cmd in ("снять", "разжаловать", "демоут"):
        if not message.guild:
            return await message.reply("❌ Команда доступна только на сервере!")
        sender_rank = await get_effective_rank(message.guild.id, message.author)
        if sender_rank < 2:
            return await message.reply("⛔️ Снимать с должности могут сотрудники от **[2] Младший модератор**!")

        target = await extract_target_discord_member(message, args)
        if not target or target.id == message.author.id:
            return await message.reply("❌ Укажите пользователя через `@упоминание` или ответом на сообщение!")

        target_rank = await get_effective_rank(message.guild.id, target)
        if sender_rank <= target_rank:
            return await message.reply(f"⛔️ Вы не можете снять пользователя равного или старшего по рангу (`[{target_rank}]`)!")

        t_db_uid = config.DISCORD_UID_OFFSET + target.id
        await db.set_user_rank(db_cid, t_db_uid, 0, granted_by=db_uid)
        await message.reply(f"🚫 **{target.mention}** снят(а) со всех должностей администрации сервера.\n👨‍💻 Снял: {message.author.mention}")
        return

    elif cmd in RANK_PROMOTIONS:
        if not message.guild:
            return await message.reply("❌ Команда доступна только на сервере!")
        req_rank = RANK_PROMOTIONS[cmd]
        sender_rank = await get_effective_rank(message.guild.id, message.author)

        if sender_rank <= req_rank and sender_rank < 10:
            return await message.reply(f"⛔️ Чтобы назначить на ступень `[{req_rank}] {RANK_NAMES[req_rank]}`, ваш ранг должен быть выше `[{req_rank}]`!")
        if sender_rank < 2:
            return await message.reply("⛔️ Назначать на должности могут сотрудники от **[2] Младший модератор**!")

        target = await extract_target_discord_member(message, args)
        if not target or target.id == message.author.id:
            return await message.reply(f"💡 Формат: `{cmd} @юзер`")

        target_rank = await get_effective_rank(message.guild.id, target)
        if sender_rank <= target_rank:
            return await message.reply(f"⛔️ Вы не можете изменять должность равного или старшего администратора (`[{target_rank}]`)!")

        t_db_uid = config.DISCORD_UID_OFFSET + target.id
        await db.set_user_rank(db_cid, t_db_uid, req_rank, granted_by=db_uid)
        icon = RANK_ICONS[req_rank]
        title = RANK_NAMES[req_rank]
        await message.reply(f"👑 **{target.mention}** назначен(а) на должность **[{req_rank}] {title} {icon}**!\n👨‍💻 Назначил: {message.author.mention}")
        return

    elif cmd in RANK_DEMOTIONS:
        if not message.guild:
            return await message.reply("❌ Команда доступна только на сервере!")
        sender_rank = await get_effective_rank(message.guild.id, message.author)
        if sender_rank < 2:
            return await message.reply("⛔️ Снимать с должностей могут сотрудники от **[2] Младший модератор**!")

        target = await extract_target_discord_member(message, args)
        if not target or target.id == message.author.id:
            return await message.reply(f"💡 Формат: `{cmd} @юзер`")

        target_rank = await get_effective_rank(message.guild.id, target)
        if sender_rank <= target_rank:
            return await message.reply(f"⛔️ Вы не можете снять должность равного или старшего по рангу (`[{target_rank}]`)!")

        t_db_uid = config.DISCORD_UID_OFFSET + target.id
        await db.set_user_rank(db_cid, t_db_uid, 0, granted_by=db_uid)
        await message.reply(f"🚫 С пользователя **{target.mention}** успешно снята должность `{cmd.lstrip('-')}`!\n👨‍💻 Снял: {message.author.mention}")
        return

    # ═══════════════════════════════════════════════════════════
    # 18. 🛡 МОДЕРАЦИЯ ЧАТА
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("кик", "kick"):
        if not message.guild:
            return await message.reply("❌ Команда доступна только на сервере!")
        sender_rank = await get_effective_rank(message.guild.id, message.author)
        if sender_rank < 2:
            return await message.reply("⛔️ Кикать могут сотрудники от **[2] Младший модератор**!")
        target = await extract_target_discord_member(message, args)
        if not target or target.id == message.author.id:
            return await message.reply("Формат: `кик @юзер [причина]`")
        target_rank = await get_effective_rank(message.guild.id, target)
        if target_rank >= sender_rank:
            return await message.reply(f"⛔️ Иммунитет! Ранг цели `[{target_rank}]` равен или выше вашего `[{sender_rank}]`!")
        reason = re.sub(r"<@!?\d+>", "", args).strip() or "Нарушение правил"
        try:
            if isinstance(target, disnake.Member):
                await target.kick(reason=reason)
                await message.reply(f"👢 **{target.mention}** исключён с сервера!\n📝 Причина: *{reason}* | Модератор: {message.author.mention}")
            else:
                await message.reply("❌ Пользователь не находится на сервере.")
        except Exception as e:
            await message.reply(f"❌ Ошибка Discord API при кике: {e}")
        return

    elif cmd in ("бан", "ban"):
        if not message.guild:
            return await message.reply("❌ Команда доступна только на сервере!")
        sender_rank = await get_effective_rank(message.guild.id, message.author)
        if sender_rank < 6:
            return await message.reply("⛔️ Банить могут сотрудники от **[6] Старший админ**!")
        target = await extract_target_discord_member(message, args)
        if not target or target.id == message.author.id:
            return await message.reply("Формат: `бан @юзер [причина]`")
        target_rank = await get_effective_rank(message.guild.id, target)
        if target_rank >= sender_rank:
            return await message.reply(f"⛔️ Иммунитет! Ранг цели `[{target_rank}]` равен или выше вашего `[{sender_rank}]`!")
        reason = re.sub(r"<@!?\d+>", "", args).strip() or "Грубое нарушение правил"
        try:
            await message.guild.ban(target, reason=reason)
            await message.reply(f"🔨 **{target.mention}** забанен на сервере!\n📝 Причина: *{reason}* | Админ: {message.author.mention}")
        except Exception as e:
            await message.reply(f"❌ Ошибка Discord API при бане: {e}")
        return

    elif cmd in ("варн", "warn"):
        if not message.guild:
            return await message.reply("❌ Команда доступна только на сервере!")
        sender_rank = await get_effective_rank(message.guild.id, message.author)
        if sender_rank < 1:
            return await message.reply("⛔️ Выдавать предупреждения могут сотрудники от **[1] Стажёр**!")
        target = await extract_target_discord_member(message, args)
        if not target or target.id == message.author.id:
            return await message.reply("Формат: `варн @юзер [причина]`")
        target_rank = await get_effective_rank(message.guild.id, target)
        if target_rank >= sender_rank:
            return await message.reply(f"⛔️ Иммунитет! Ранг цели `[{target_rank}]` равен или выше вашего `[{sender_rank}]`!")
        reason = re.sub(r"<@!?\d+>", "", args).strip() or "Нарушение порядка"
        t_db_uid = config.DISCORD_UID_OFFSET + target.id
        w_c = await db.add_warn(db_cid, t_db_uid, db_uid, reason)
        if w_c >= 3:
            try:
                if isinstance(target, disnake.Member):
                    await target.kick(reason="Превышен лимит предупреждений (3/3 варнов)")
                    return await message.reply(f"⚠️ **{target.mention}** получил(а) 3-й варн и был **исключён(а)** с сервера!")
            except Exception:
                pass
        await message.reply(f"⚠️ **{target.mention}** получил(а) предупреждение `[{w_c}/3]`!\n📝 Причина: *{reason}* | Выдал: {message.author.mention}")
        return

    elif cmd in ("варны", "warns"):
        target = await extract_target_discord_member(message, args) or message.author
        t_db_uid = config.DISCORD_UID_OFFSET + target.id
        warn_list = await db.get_user_warns(db_cid, t_db_uid)
        if not warn_list:
            return await message.reply(f"🕊 У пользователя **{target.mention}** нет активных предупреждений.")
        lines = [f"⚠️ **Предупреждения {target.mention} ({len(warn_list)}/3):**"]
        for idx, w in enumerate(warn_list, 1):
            lines.append(f"{idx}. {w.get('reason', 'Без причины')} (ID: {w.get('id')})")
        await message.reply("\n".join(lines))
        return

    elif cmd in ("снятьварн", "снять варн", "unwarn"):
        if not message.guild:
            return await message.reply("❌ Команда доступна только на сервере!")
        sender_rank = await get_effective_rank(message.guild.id, message.author)
        if sender_rank < 2:
            return await message.reply("⛔️ Снимать предупреждения могут сотрудники от **[2] Младший модератор**!")
        target = await extract_target_discord_member(message, args)
        if not target:
            return await message.reply("Формат: `снятьварн @юзер`")
        t_db_uid = config.DISCORD_UID_OFFSET + target.id
        await db.remove_last_warn(db_cid, t_db_uid)
        await message.reply(f"✅ Одно предупреждение снято с пользователя **{target.mention}**.\n👨‍💻 Модератор: {message.author.mention}")
        return

    elif cmd in ("мут", "mute"):
        if not message.guild:
            return await message.reply("❌ Команда доступна только на сервере!")
        sender_rank = await get_effective_rank(message.guild.id, message.author)
        if sender_rank < 1:
            return await message.reply("⛔️ Мутить участников могут сотрудники от **[1] Стажёр**!")
        target = await extract_target_discord_member(message, args)
        if not target or target.id == message.author.id:
            return await message.reply("Формат: `мут @юзер [минут] [причина]`")
        target_rank = await get_effective_rank(message.guild.id, target)
        if target_rank >= sender_rank:
            return await message.reply(f"⛔️ Иммунитет! Ранг цели `[{target_rank}]` равен или выше вашего `[{sender_rank}]`!")
        clean_args = re.sub(r"<@!?\d+>", "", args).strip()
        num_m = re.search(r"\b(\d+)\b", clean_args)
        minutes = int(num_m.group(1)) if num_m else 10
        reason = re.sub(r"\b\d+\b", "", clean_args).strip() or "Флуд / Спам"
        try:
            if isinstance(target, disnake.Member):
                until = disnake.utils.utcnow() + datetime.timedelta(minutes=minutes)
                await target.timeout(until=until, reason=reason)
                await message.reply(f"🔇 **{target.mention}** отправлен(а) подумать на **{minutes} мин.**!\n📝 Причина: *{reason}* | Модератор: {message.author.mention}")
            else:
                await message.reply("❌ Пользователь не на сервере.")
        except Exception as e:
            await message.reply(f"❌ Ошибка таймаута Discord: {e}")
        return

    elif cmd in ("размут", "unmute"):
        if not message.guild:
            return await message.reply("❌ Команда доступна только на сервере!")
        sender_rank = await get_effective_rank(message.guild.id, message.author)
        if sender_rank < 1:
            return await message.reply("⛔️ Размучивать могут сотрудники от **[1] Стажёр**!")
        target = await extract_target_discord_member(message, args)
        if not target:
            return await message.reply("Формат: `размут @юзер`")
        try:
            if isinstance(target, disnake.Member):
                await target.timeout(until=None, reason="Размут модератором")
                await message.reply(f"🔊 С пользователя **{target.mention}** сняты ограничения на общение!\n👨‍💻 Модератор: {message.author.mention}")
            else:
                await message.reply("❌ Пользователь не на сервере.")
        except Exception as e:
            await message.reply(f"❌ Ошибка снятия таймаута: {e}")
        return

    # ═══════════════════════════════════════════════════════════
    # 19. 🆘 СЛУЖБА ПОДДЕРЖКИ И ТИКЕТЫ
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("поддержка", "тикет", "support", "ticket"):
        if not args:
            return await message.reply("💡 Напишите: `тикет [описание вашей проблемы или вопроса]`")

        # Создаем тикет в БД
        tid = await db.create_support_ticket(
            user_id=db_uid,
            user_name=str(message.author),
            text=args[:1000],
            status="open",
            platform="discord",
            platform_peer_id=message.channel.id
        )

        embed = disnake.Embed(
            title=f"🆘 НОВОЕ ОБРАЩЕНИЕ В ТЕХПОДДЕРЖКУ #{tid}",
            description=(
                f"👤 **От:** {message.author.mention} (`{message.author.id}`)\n"
                f"📝 **Проблема:**\n«{args[:1000]}»\n\n"
                f"⏳ **Статус:** 🟢 Открыт (Ожидает стаффа)"
            ),
            color=disnake.Color.gold()
        )
        t_view = DiscordTicketView(ticket_id=tid)
        await message.channel.send(embed=embed, view=t_view)
        await message.reply(f"✅ Ваше обращение принято (Тикет `#{tid}`)! Сотрудники администрации скоро ответят.")
        return




    # ═══════════════════════════════════════════════════════════
    # 20. 🎮 MINECRAFT SUITE
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("сервер", "пинг", "mc", "пинг сервера"):
        if not args:
            embed = disnake.Embed(
                title="⛏ Мониторинг серверов Minecraft",
                description=(
                    "Чтобы узнать статус и онлайн сервера, укажите его IP-адрес:\n\n"
                    "📌 **Как пользоваться командой:**\n"
                    "• `сервер адрес_сервера` или `пинг адрес_сервера`\n"
                    "• или слэш-команда: `/сервер ip:адрес_сервера`\n\n"
                    "🔍 *Пример:* `сервер play.myserver.ru` или `сервер 127.0.0.1:25565`"
                ),
                color=disnake.Color.blurple()
            )
            return await message.reply(embed=embed)
        status_msg = await message.reply("🔍 Опрашиваю сервер Minecraft...")
        srv_ip = args.strip()
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://api.mcsrvstat.us/2/{srv_ip}", timeout=aiohttp.ClientTimeout(total=5.0)) as r:
                    data = await r.json()
        except Exception as e:
            return await status_msg.edit(content=f"❌ Ошибка подключения к серверу `{srv_ip}`: {e}")

        is_online = data.get("online", False)
        if not is_online:
            embed = disnake.Embed(
                title=f"🔴 СЕРВЕР ОФЛАЙН · {srv_ip}",
                description="Сервер недоступен или указан неверный адрес.",
                color=disnake.Color.red()
            )
            return await status_msg.edit(content=None, embed=embed)

        pl = data.get("players", {})
        on_p = pl.get("online", 0)
        max_p = pl.get("max", 0)
        ver = data.get("version", "Неизвестно")
        motd_lines = data.get("motd", {}).get("clean", [])
        motd_text = "\n".join(motd_lines) if motd_lines else "Нет описания"

        embed = disnake.Embed(
            title=f"🟢 МОНИТОРИНГ СЕРВЕРА MINECRAFT",
            description=f"🌐 **Адрес:** `{srv_ip}`\n\n📝 **MOTD:**\n```\n{motd_text[:300]}\n```",
            color=disnake.Color.green()
        )
        embed.add_field(name="👥 Игроки онлайн", value=f"`{on_p:,} / {max_p:,}`", inline=True)
        embed.add_field(name="⚙️ Версия", value=f"`{ver}`", inline=True)
        embed.set_thumbnail(url=f"https://api.mcsrvstat.us/icon/{srv_ip}")
        embed.set_footer(text="MOXXI Minecraft Module")
        await status_msg.edit(content=None, embed=embed)
        return

    elif cmd in ("скин", "skin"):
        if not args:
            embed = disnake.Embed(
                title="👕 Просмотр 3D скинов Minecraft",
                description=(
                    "Чтобы посмотреть 3D скин игрока, укажите его никнейм:\n\n"
                    "📌 **Как пользоваться командой:**\n"
                    "• `скин никнейм`\n"
                    "• или слэш-команда: `/скин ник:никнейм`\n\n"
                    "🔍 *Пример:* `скин Steve`"
                ),
                color=disnake.Color.blurple()
            )
            return await message.reply(embed=embed)
        nick = args.strip().split()[0]
        embed = disnake.Embed(
            title=f"👕 3D СКИН ИГРОКА: {nick}",
            description=f"📥 [Скачать скин](https://minotar.net/download/{nick})",
            color=disnake.Color.from_rgb(0, 242, 254)
        )
        embed.set_image(url=f"https://mc-heads.net/body/{nick}/right")
        embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{nick}")
        embed.set_footer(text="MOXXI Minecraft Tools")
        await message.reply(embed=embed)
        return

    elif cmd in ("голова", "head"):
        if not args:
            return await message.reply("💡 Укажите ник игрока! Пример: `голова Notch`")
        nick = args.strip().split()[0]
        embed = disnake.Embed(
            title=f"👤 АВАТАР ИГРОКА: {nick}",
            color=disnake.Color.from_rgb(0, 242, 254)
        )
        embed.set_image(url=f"https://mc-heads.net/avatar/{nick}/256")
        await message.reply(embed=embed)
        return

    elif cmd in ("привязать_ник", "привязать ник", "ник_мс"):
        if not args:
            return await message.reply("💡 Укажите ваш игровой никнейм Minecraft! Пример: `привязать_ник Steve`")
        mc_name = args.strip().split()[0]
        await db.set_user_mc_nick(db_uid, mc_name)
        await message.reply(f"🎮 Ваш никнейм Minecraft **`{mc_name}`** успешно привязан к профилю MOXXI!")
        return

    elif cmd in ("панель_верификации", "панель верификации", "верификация"):
        if not message.guild:
            return await message.reply("❌ Доступно только на сервере!")
        sender_rank = await get_effective_rank(message.guild.id, message.author)
        if sender_rank < 8:
            return await message.reply("⛔️ Создавать панель верификации могут сотрудники от **[8] Тех. администратор**!")

        role_name = args.strip() or "Участник"
        embed = disnake.Embed(
            title="🛡 ВЕРИФИКАЦИЯ НА СЕРВЕРЕ",
            description=(
                f"Добро пожаловать на сервер **{message.guild.name}**!\n\n"
                f"Чтобы получить полный доступ ко всем текстовым и голосовым каналам, "
                f"нажмите на зелёную кнопку ниже:\n\n"
                f"👇 **Нажмите для прохождения верификации:**"
            ),
            color=disnake.Color.green()
        )
        view = disnake.ui.View(timeout=None)
        view.add_item(disnake.ui.Button(
            label="✅ Пройти верификацию",
            style=disnake.ButtonStyle.success,
            custom_id=f"dc_verify:{role_name}",
            emoji="🔓"
        ))
        await message.channel.send(embed=embed, view=view)
        try:
            await message.delete()
        except Exception:
            pass
        return

    # ═══════════════════════════════════════════════════════════
    # 21. 🎉 GIVEAWAYS SUITE
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("розыгрыш", "giveaway", "конкурс"):
        if not message.guild:
            return await message.reply("❌ Розыгрыши доступны только на сервере!")
        sender_rank = await get_effective_rank(message.guild.id, message.author)
        if sender_rank < 3:
            return await message.reply("⛔️ Создавать розыгрыши могут сотрудники от **[3] Старший модератор**!")

        parts = args.split(maxsplit=2)
        if len(parts) < 3 or not parts[0].isdigit() or not parts[1].isdigit():
            return await message.reply("💡 Формат: `розыгрыш [минут] [победителей] [приз]`\nПример: `розыгрыш 15 1 50 000 монет`")

        duration_min = int(parts[0])
        winners_count = int(parts[1])
        prize = parts[2].strip()

        duration_sec = duration_min * 60
        ends_at = int(time.time()) + duration_sec

        embed = disnake.Embed(
            title="🎉 РОЗЫГРЫШ ПРИЗОВ · GIVEAWAY",
            description=(
                f"🎁 **Приз:** **{prize}**\n"
                f"👑 **Победителей:** `{winners_count}`\n"
                f"⏱ **Длительность:** `{duration_min} мин.`\n"
                f"👨‍💻 **Организатор:** {message.author.mention}\n\n"
                f"👇 Нажмите кнопку ниже, чтобы принять участие!"
            ),
            color=disnake.Color.purple()
        )
        view = disnake.ui.View(timeout=None)
        # Placeholder view until message is sent
        btn_gw = disnake.ui.Button(label="🎉 Участвовать (0)", style=disnake.ButtonStyle.primary, custom_id="dc_gw_temp")
        view.add_item(btn_gw)

        gw_msg = await message.channel.send(embed=embed, view=view)
        gw_id = await db.create_giveaway(message.channel.id, gw_msg.id, prize, winners_count, duration_sec, message.author.id)

        # Update button with real custom_id
        real_view = disnake.ui.View(timeout=None)
        real_view.add_item(disnake.ui.Button(label="🎉 Участвовать (0)", style=disnake.ButtonStyle.primary, custom_id=f"dc_gw_join:{gw_id}"))
        await gw_msg.edit(view=real_view)
        try:
            await message.delete()
        except Exception:
            pass
        return

    # ═══════════════════════════════════════════════════════════
    # 22. 🏆 LEVELING & XP SUITE
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("уровень", "лвл"):
        target = await extract_target_discord_member(message, args) or message.author
        t_db_uid = config.DISCORD_UID_OFFSET + target.id
        tu = await db.get_user(t_db_uid) or {}
        xp = tu.get("xp", 0)
        msgs = tu.get("messages", 0)

        lvl = max(1, int((xp / 100) ** 0.5) + 1)
        prev_lvl_xp = ((lvl - 1) ** 2) * 100
        next_lvl_xp = (lvl ** 2) * 100
        progress_xp = max(0, xp - prev_lvl_xp)
        step_needed = max(1, next_lvl_xp - prev_lvl_xp)
        percent = int((progress_xp / step_needed) * 100)
        bar = build_progress_bar(progress_xp, step_needed, 10)

        embed = disnake.Embed(
            title=f"📊 Уровень активности — {target.display_name}",
            color=disnake.Color.from_rgb(0, 230, 118)
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🎖 Уровень", value=f"**Уровень {lvl}**", inline=True)
        embed.add_field(name="⚡️ Опыт", value=f"`{xp:,} XP`", inline=True)
        embed.add_field(name="💬 Сообщений", value=f"`{msgs:,}`", inline=True)
        embed.add_field(
            name="📈 Прогресс до следующего уровня",
            value=f"`[{bar}]` {progress_xp}/{step_needed} XP ({percent}%)",
            inline=False
        )
        await message.reply(embed=embed)
        return

    elif cmd in ("топ_уровень", "топ_лвл", "топ уровень", "топ лвл", "levels"):
        top_rows = await db.get_top_level(10)
        lines = ["🏆 **ТОП-10 АКТИВНЫХ УЧАСТНИКОВ СЕРВЕРА (XP)**", "━━━━━━━━━━━━━━━━━━━━"]
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for idx, r in enumerate(top_rows):
            m_id = r["user_id"] - config.DISCORD_UID_OFFSET
            name = r.get("first_name") or r.get("username") or f"ID {m_id}"
            lines.append(f"{medals[idx]} **{name}** — `{r.get('level', 1)} ур.` (`{r.get('xp', 0):,} XP`)")
        embed = disnake.Embed(
            title="📈 ТАБЛИЦА ЛИДЕРОВ ПО ОПЫТУ",
            description="\n".join(lines),
            color=disnake.Color.gold()
        )
        await message.reply(embed=embed)
        return

    # ═══════════════════════════════════════════════════════════
    # 23. 🛡 MODERATION & INFO SUITE
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("очистить", "clear", "purge"):
        if not message.guild:
            return await message.reply("❌ Доступно только на сервере!")
        sender_rank = await get_effective_rank(message.guild.id, message.author)
        if sender_rank < 2:
            return await message.reply("⛔️ Очищать сообщения могут сотрудники от **[2] Младший модератор**!")

        clean_args = re.sub(r"<@!?\d+>", "", args).strip()
        num_m = re.search(r"\b(\d+)\b", clean_args)
        count = int(num_m.group(1)) if num_m else 10
        count = min(100, max(1, count))

        try:
            deleted = await message.channel.purge(limit=count + 1)
            temp = await message.channel.send(f"🧹 Удалено сообщений: **{len(deleted) - 1}**! (Модератор: {message.author.mention})")
            await asyncio.sleep(4.0)
            await temp.delete()
        except Exception as e:
            await message.reply(f"❌ Ошибка чистки сообщений: {e}")
        return

    elif cmd in ("сервер_инфо", "сервер инфо"):
        if not message.guild:
            return await message.reply("❌ Доступно только на сервере!")
        g = message.guild
        owner = g.get_member(g.owner_id)
        owner_name = owner.mention if owner else f"<@{g.owner_id}>"
        c_date = g.created_at.strftime("%d.%m.%Y %H:%M")

        embed = disnake.Embed(
            title=f"🏰 ИНФОРМАЦИЯ О СЕРВЕРЕ: {g.name}",
            color=disnake.Color.from_rgb(155, 89, 182)
        )
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="👑 Создатель", value=owner_name, inline=True)
        embed.add_field(name="👥 Участников", value=f"`{g.member_count:,}`", inline=True)
        embed.add_field(name="🚀 Бустов", value=f"`{g.premium_subscription_count}` (Уровень {g.premium_tier})", inline=True)
        embed.add_field(name="💬 Текстовых каналов", value=f"`{len(g.text_channels)}`", inline=True)
        embed.add_field(name="🔊 Голосовых каналов", value=f"`{len(g.voice_channels)}`", inline=True)
        embed.add_field(name="🎭 Ролей", value=f"`{len(g.roles)}`", inline=True)
        embed.add_field(name="📅 Дата создания", value=f"`{c_date}`", inline=False)
        await message.reply(embed=embed)
        return

    elif cmd in ("юзер_инфо", "юзер инфо"):
        target = await extract_target_discord_member(message, args) or message.author
        reg_date = target.created_at.strftime("%d.%m.%Y")
        join_date = target.joined_at.strftime("%d.%m.%Y") if isinstance(target, disnake.Member) and target.joined_at else "Неизвестно"
        t_db_uid = config.DISCORD_UID_OFFSET + target.id
        tu = await db.get_user(t_db_uid) or {}

        embed = disnake.Embed(
            title=f"👤 ДОСЬЕ ПОЛЬЗОВАТЕЛЯ: {target.display_name}",
            color=disnake.Color.from_rgb(52, 152, 219)
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🆔 ID", value=f"`{target.id}`", inline=True)
        embed.add_field(name="💰 Баланс", value=f"`{tu.get('balance', 0):,}` 🌑", inline=True)
        embed.add_field(name="🎖 Уровень", value=f"`{tu.get('level', 1)} ур.`", inline=True)
        embed.add_field(name="📅 Регистрация в Discord", value=f"`{reg_date}`", inline=True)
        embed.add_field(name="📥 Вход на сервер", value=f"`{join_date}`", inline=True)
        if isinstance(target, disnake.Member):
            roles_str = ", ".join([r.mention for r in target.roles[1:][:8]]) or "Нет ролей"
            embed.add_field(name="🎭 Роли", value=roles_str, inline=False)
        await message.reply(embed=embed)
        return

    # ═══════════════════════════════════════════════════════════
    # 24. 💼 ECONOMY & WORK SUITE
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("работа", "работать", "work", "смена"):
        now_ts = int(time.time())
        last_w = u_data.get("last_work_ts", 0) or 0
        if now_ts - last_w < 3600:
            left_m = int((3600 - (now_ts - last_w)) / 60)
            return await message.reply(f"⏳ Вы уже отработали смену! Отдохните ещё **{left_m} мин.**")

        lvl = u_data.get("level", 1) or 1
        jobs = [
            ("Курьер пиццы", 500, 1000),
            ("Бариста в кофейне", 1000, 2000),
            ("IT-Разработчик", 2000, 4000),
            ("Трейдер на бирже", 3500, 6500),
            ("Гендиректор холдинга", 5000, 10000),
        ]
        job_idx = min(len(jobs) - 1, int(lvl / 3))
        j_name, min_pay, max_pay = jobs[job_idx]
        earned = random.randint(min_pay, max_pay)

        await db.add_balance(db_uid, earned)
        await db.update_user_action_cooldown(db_uid, "work")
        await db.add_user_xp(db_uid, 35)

        embed = disnake.Embed(
            title=f"💼 ТРУДОВАЯ СМЕНА: {j_name}",
            description=f"Отличная работа, {message.author.mention}! Вы успешно завершили смену.\n💰 Зарплата: **`+{earned:,}` 🌑 монет**\n⚡️ Опыт: `+35 XP`",
            color=disnake.Color.green()
        )
        await message.reply(embed=embed)
        return

    elif cmd in ("попрошайничать", "бомжевать", "beg"):
        now_ts = int(time.time())
        last_b = u_data.get("last_beg_ts", 0) or 0
        if now_ts - last_b < 120:
            left_s = 120 - (now_ts - last_b)
            return await message.reply(f"⏳ Вы сможете снова попросить монет через **{left_s} сек.**")

        donors = [
            ("Илон Маск", 250, "Поделился карманными деньгами!"),
            ("Добрая бабушка у метро", 120, "Дала монетку на пирожок."),
            ("Мистер Бист", 450, "Снял челлендж и дал тебе котлету монет!"),
            ("Уличный кот", 30, "Принёс блестящую монетку в зубах."),
            ("Прохожий миллионер", 300, "Оценил твой энтузиазм.")
        ]
        donor_name, pay, note = random.choice(donors)
        await db.add_balance(db_uid, pay)
        await db.update_user_action_cooldown(db_uid, "beg")

        embed = disnake.Embed(
            title=f"🪙 {donor_name}",
            description=f"«{note}»\n\n💰 Получено: **`+{pay:,}` 🌑 монет**",
            color=disnake.Color.gold()
        )
        await message.reply(embed=embed)
        return

    elif cmd in ("криминал", "crime"):
        now_ts = int(time.time())
        last_c = u_data.get("last_crime_ts", 0) or 0
        if now_ts - last_c < 600:
            left_m = int((600 - (now_ts - last_c)) / 60)
            return await message.reply(f"🚨 Полиция ещё ищет вас в районе! Залягте на дно на **{left_m} мин.**")

        await db.update_user_action_cooldown(db_uid, "crime")
        success = random.random() < 0.55
        if success:
            loot = random.randint(2500, 8500)
            await db.add_balance(db_uid, loot)
            embed = disnake.Embed(
                title="🥷 УСПЕШНОЕ ОГРАБЛЕНИЕ!",
                description=f"Вы взломали инкассаторский терминал и скрылись без следа!\n💰 Куш: **`+{loot:,}` 🌑 монет**!",
                color=disnake.Color.green()
            )
        else:
            fine = random.randint(1000, 3000)
            await db.add_balance(db_uid, -fine)
            embed = disnake.Embed(
                title="🚨 ОБЛАВА ПОЛИЦИИ!",
                description=f"Сигнализация сработала! Вас задержали и выписали крупный штраф.\n💸 Потеряно: **`-{fine:,}` 🌑 монет**!",
                color=disnake.Color.red()
            )
        await message.reply(embed=embed)
        return

    elif cmd in ("магазин", "шоп", "shop"):
        embed = disnake.Embed(
            title="🛒 СУПЕРМАРКЕТ MOXXI · ПРЕДМЕТЫ И БАФФЫ",
            description=(
                "Купить предмет: `купить [номер]`\n\n"
                "1️⃣ 🛡 **Бронированный Сейф** — `25 000 🌑`\n"
                "   *100% защита баланса от ограблений других игроков на 7 дней.*\n\n"
                "2️⃣ ⚡️ **XP Бустер x2** — `15 000 🌑`\n"
                "   *Удваивает весь получаемый опыт за общение на 24 часа.*\n\n"
                "3️⃣ 🎫 **Лотерейный Билет** — `1 000 🌑`\n"
                "   *Моментальный розыгрыш: шанс выиграть до 100 000 монет!*\n\n"
                "4️⃣ 👑 **Золотой Престиж** — `50 000 🌑`\n"
                "   *Эксклюзивная золотая аура и плашка в профиле.*"
            ),
            color=disnake.Color.from_rgb(241, 196, 15)
        )
        await message.reply(embed=embed)
        return

    elif cmd in ("купить",):
        clean_args = args.strip()
        cur_bal = u_data.get("balance", 0)
        if clean_args == "1":
            if cur_bal < 25000:
                return await message.reply("❌ Недостаточно монет! Сейф стоит **25 000 🌑**.")
            await db.add_balance(db_uid, -25000)
            until = await db.set_user_safe(db_uid, 7 * 86400)
            u_date = datetime.datetime.fromtimestamp(until).strftime("%d.%m.%Y")
            return await message.reply(f"🛡 **Бронированный Сейф активирован!** Ваши сбережения защищены от грабежей до **{u_date}**!")

        elif clean_args == "2":
            if cur_bal < 15000:
                return await message.reply("❌ Недостаточно монет! XP Бустер стоит **15 000 🌑**.")
            await db.add_balance(db_uid, -15000)
            until = await db.set_user_xp_booster(db_uid, 86400)
            return await message.reply("⚡️ **XP Бустер x2 активирован на 24 часа!** Теперь вы получаете удвоенный опыт за сообщения!")

        elif clean_args == "3":
            if cur_bal < 1000:
                return await message.reply("❌ Билет стоит **1 000 🌑**!")
            await db.add_balance(db_uid, -1000)
            roll = random.random()
            if roll < 0.05:
                win = 50000
                res = "🎉 ДЖЕКПОТ!"
            elif roll < 0.25:
                win = 5000
                res = "✨ Крупный выигрыш!"
            elif roll < 0.60:
                win = 1500
                res = "👍 Небольшой выигрыш!"
            else:
                win = 0
                res = "💨 Билет оказался пустым!"
            if win > 0:
                await db.add_balance(db_uid, win)
            return await message.reply(f"🎫 **Лотерейный билет стёрт:** {res}\n💰 Выплата: **`+{win:,}` 🌑 монет**!")

        else:
            return await message.reply("💡 Выберите товар: `купить 1` (Сейф), `купить 2` (Бустер), `купить 3` (Лотерея)!")

    elif cmd in ("инвентарь", "инв", "inv", "рюкзак"):
        now_ts = int(time.time())
        safe_u = u_data.get("safe_until", 0) or 0
        booster_u = u_data.get("xp_booster_until", 0) or 0
        mc_n = u_data.get("mc_nick", "") or "Не привязан"

        safe_status = f"🟢 Активен до {datetime.datetime.fromtimestamp(safe_u).strftime('%d.%m %H:%M')}" if safe_u > now_ts else "⚪️ Отсутствует"
        boost_status = f"🟢 Активен (x2 XP)" if booster_u > now_ts else "⚪️ Отсутствует"

        embed = disnake.Embed(
            title=f"🎒 ИНВЕНТАРЬ И БАФФЫ: {message.author.display_name}",
            color=disnake.Color.from_rgb(46, 204, 113)
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.add_field(name="🛡 Бронированный сейф", value=safe_status, inline=True)
        embed.add_field(name="⚡️ XP Бустер", value=boost_status, inline=True)
        embed.add_field(name="🎮 Ник Minecraft", value=f"`{mc_n}`", inline=True)
        embed.add_field(name="💰 Наличные", value=f"`{u_data.get('balance', 0):,}` 🌑", inline=True)
        embed.add_field(name="🏦 В банке", value=f"`{u_data.get('bank', 0):,}` 🌑", inline=True)
        await message.reply(embed=embed)
        return

    # ═══════════════════════════════════════════════════════════
    # 25. 📩 SUPPORT & TICKET SUITE
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("панель_тикетов", "панель тикетов"):
        if not message.guild:
            return await message.reply("❌ Доступно только на сервере!")
        sender_rank = await get_effective_rank(message.guild.id, message.author)
        if sender_rank < 8:
            return await message.reply("⛔️ Создавать панель тикетов могут сотрудники от **[8] Тех. администратор**!")

        embed = disnake.Embed(
            title="🆘 СЛУЖБА ПОДДЕРЖКИ СЕРВЕРА",
            description=(
                "Если у вас возникла проблема, вопрос по серверу, жалоба или вопрос по оплате:\n\n"
                "👇 **Нажмите кнопку ниже, чтобы открыть тикет с администрацией:**"
            ),
            color=disnake.Color.from_rgb(155, 89, 182)
        )
        view = disnake.ui.View(timeout=None)
        view.add_item(disnake.ui.Button(
            label="📩 Открыть тикет",
            style=disnake.ButtonStyle.primary,
            custom_id="dc_open_ticket_panel",
            emoji="✍️"
        ))
        await message.channel.send(embed=embed, view=view)
        try:
            await message.delete()
        except Exception:
            pass
        return


@bot.event
async def on_button_click(inter: disnake.MessageInteraction):
    cid = inter.component.custom_id
    if not cid or not cid.startswith("dc_t_"):
        return

    # Parse dc_t_action:ticket_id
    parts = cid.split(":", 1)
    act = parts[0]
    tid = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    if not tid:
        return

    ticket = await db.get_support_ticket(tid)
    if not ticket:
        return await inter.response.send_message("❌ Тикет не найден в базе!", ephemeral=True)

    sender_rank = await get_effective_rank(inter.guild.id, inter.author) if inter.guild else 1
    if sender_rank < 1:
        return await inter.response.send_message("⛔️ Доступно только администрации сервера!", ephemeral=True)

    if act == "dc_t_claim":
        c_by = ticket.get("claimed_by", 0)
        if c_by and c_by != inter.author.id:
            c_name = ticket.get("claimed_name") or "другим сотрудником"
            return await inter.response.send_message(f"🔒 Этот тикет уже занят сотрудником: {c_name}!", ephemeral=True)
        await db.claim_support_ticket(tid, inter.author.id, inter.author.display_name)
        new_view = DiscordTicketView(ticket_id=tid, claimed_by=inter.author.id, claimed_name=inter.author.display_name)
        cl_embed = inter.message.embeds[0] if inter.message.embeds else disnake.Embed(title=f"Тикет #{tid}")
        cl_embed.color = disnake.Color.orange()
        cl_embed.set_footer(text=f"🔒 Взят в работу: {inter.author.display_name}")
        await inter.response.edit_message(embed=cl_embed, view=new_view)

    elif act == "dc_t_release":
        c_by = ticket.get("claimed_by", 0)
        is_owner = (inter.guild and inter.guild.owner_id == inter.author.id) or sender_rank >= 9
        if c_by and c_by != inter.author.id and not is_owner:
            return await inter.response.send_message("❌ Освободить тикет может только тот сотрудник, кто его взял!", ephemeral=True)
        await db.release_support_ticket(tid)
        new_view = DiscordTicketView(ticket_id=tid, claimed_by=0)
        cl_embed = inter.message.embeds[0] if inter.message.embeds else disnake.Embed(title=f"Тикет #{tid}")
        cl_embed.color = disnake.Color.gold()
        cl_embed.set_footer(text="🔄 Освобождён в общий пул (сложная ситуация)")
        await inter.response.edit_message(embed=cl_embed, view=new_view)
        await inter.channel.send(f"🔄 Тикет **#{tid}** освобождён сотрудником {inter.author.mention} и возвращён в общий пул!")

    elif act == "dc_t_answer":
        c_by = ticket.get("claimed_by", 0)
        if c_by and c_by != inter.author.id:
            c_name = ticket.get("claimed_name") or "другой сотрудник"
            return await inter.response.send_message(f"❌ Тикет занят: {c_name}!", ephemeral=True)
        await inter.response.send_modal(TicketAnswerModal(ticket_id=tid, ticket=ticket))

    elif act == "dc_t_reject":
        c_by = ticket.get("claimed_by", 0)
        if c_by and c_by != inter.author.id and sender_rank < 9:
            return await inter.response.send_message("❌ Отклонить чужой тикет может только старший администратор!", ephemeral=True)
        await db.close_support_ticket(tid, reason="Отклонено администратором")
        cl_embed = inter.message.embeds[0] if inter.message.embeds else disnake.Embed(title=f"Тикет #{tid}")
        cl_embed.color = disnake.Color.red()
        cl_embed.add_field(name="⛔️ Отклонён", value=f"Модератор: {inter.author.mention}", inline=False)
        await inter.response.edit_message(embed=cl_embed, view=None)

    # --- Giveaway Join Button ---
    elif cid.startswith("dc_gw_join:"):
        gw_id = int(cid.split(":", 1)[1])
        success, total_count = await db.join_giveaway(gw_id, inter.author.id)
        if not success:
            return await inter.response.send_message("⚠️ Вы уже принимаете участие в этом розыгрыше!", ephemeral=True)
        # Update button counter
        try:
            view = disnake.ui.View(timeout=None)
            view.add_item(disnake.ui.Button(label=f"🎉 Участвовать ({total_count})", style=disnake.ButtonStyle.primary, custom_id=cid))
            await inter.message.edit(view=view)
        except Exception:
            pass
        await inter.response.send_message("🎉 **Вы успешно зарегистрированы в розыгрыше!** Желаем удачи!", ephemeral=True)

    # --- Verification Button ---
    elif cid.startswith("dc_verify:"):
        role_name = cid.split(":", 1)[1]
        guild = inter.guild
        if not guild:
            return
        role = disnake.utils.get(guild.roles, name=role_name)
        if not role:
            try:
                role = await guild.create_role(name=role_name, reason="Авто-роль для верификации MOXXI")
            except Exception as e:
                return await inter.response.send_message(f"❌ Ошибка выдачи роли (нет прав у бота): {e}", ephemeral=True)
        try:
            await inter.author.add_roles(role, reason="Успешная верификация через MOXXI")
            await inter.response.send_message(f"🎉 **Поздравляем!** Вы успешно прошли верификацию и получили роль **{role.name}**!", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"❌ Ошибка присвоения роли: {e}", ephemeral=True)

    # ═══════════════════════════════════════════════════════════
    # 26. ВОРДЛ / WORDLE (Мини-игра со словами 🟩🟨⬛)
    # ═══════════════════════════════════════════════════════════
    elif cmd in ("вордл", "wordle"):
        user_id = message.author.id
        guess_word = args.strip() if args else None
        if not guess_word:
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
                    f"💡 Чтобы сделать ход, напишите: `вордл [слово]` или `/вордл [слово]`!"
                ),
                color=disnake.Color.blurple()
            )
            await message.reply(embed=embed)
            return

        embed, is_won, is_over, reward = wordle_game.process_guess(user_id, guess_word)
        if is_won and reward > 0:
            await db.add_balance(db_uid, reward)
            await db.add_user_xp(db_uid, 100)
        await message.reply(embed=embed)
        return

    # --- Ticket Panel Button ---
    elif cid == "dc_open_ticket_panel":
        # Create ticket for user
        tid = await db.create_support_ticket(
            user_id=config.DISCORD_UID_OFFSET + inter.author.id,
            user_name=str(inter.author),
            text="Обращение открыто через панель поддержки",
            status="open",
            platform="discord",
            platform_peer_id=inter.channel.id
        )
        embed = disnake.Embed(
            title=f"🆘 ТИКЕТ В ПОДДЕРЖКУ #{tid}",
            description=f"👤 **Игрок:** {inter.author.mention}\n⏳ **Статус:** Ожидает сотрудника",
            color=disnake.Color.gold()
        )
        await inter.channel.send(embed=embed, view=DiscordTicketView(ticket_id=tid))
        await inter.response.send_message(f"✅ Тикет **#{tid}** успешно создан! Опишите вашу проблему прямо здесь.", ephemeral=True)



async def main():
    token = config.DISCORD_BOT_TOKEN
    if not token or token == "YOUR_TOKEN_HERE":
        log.warning("DISCORD_BOT_TOKEN не задан в config.py!")
        return

    await db.init()
    log.info("Запуск Discord бота MOXXI 3.0 Ultimate...")
    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
