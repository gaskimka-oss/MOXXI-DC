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
intents.members = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(*config.PREFIXES),
    intents=intents,
    case_insensitive=True,
    help_command=None
)

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
            await inter.channel.send(embed=embed)
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
        super().__init__(placeholder="Выберите раздел команд...", min_values=1, max_values=1, options=options)

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
        embed.add_field(name="⭐ Опыт / Уровень", value=f"`{u_data.get('level', 1)} ур. ({u_data.get('xp', 0)} XP)`", inline=True)
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


# ═══════════════════════════════════════════════════════════════
# 🚀 СОБЫТИЯ DISCORD
# ═══════════════════════════════════════════════════════════════
@bot.event
async def on_ready():
    log.info("Бот MOXXI Discord успешно вошел как: %s (ID: %d)", bot.user, bot.user.id)
    bot.add_view(MainMenuView())
    bot.add_view(HelpView())
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

    # Проверка префикса
    has_prefix = False
    for pfx in config.PREFIXES:
        if clean_txt.startswith(pfx):
            clean_txt = clean_txt[len(pfx):].strip()
            has_prefix = True
            break

    if not has_prefix and not bot.user.mentioned_in(message):
        return

    if bot.user.mentioned_in(message):
        clean_txt = clean_txt.replace(bot.user.mention, "").strip()

    parts = clean_txt.split()
    if not parts:
        return
    cmd = parts[0].lower()
    args = clean_txt[len(parts[0]):].strip()

    db_uid = config.DISCORD_UID_OFFSET + message.author.id
    db_cid = config.DISCORD_UID_OFFSET + (message.guild.id if message.guild else message.channel.id)

    await db.ensure_user(db_uid, username=str(message.author), first_name=message.author.display_name)
    u_data = await db.get_user(db_uid) or {}

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
        embed.add_field(name="⭐ Опыт / Уровень", value=f"`{u_data.get('level', 1)} ур. ({u_data.get('xp', 0)} XP)`", inline=True)
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
