"""Extra Slash Commands Suite for MOXXI Discord Bot.
Includes:
- Pets & Expeditions Suite (/питомец, /приручить, /покормить, /экспедиция, /забрать_добычу)
- Cars, Garage & Races Suite (/автосалон, /купить_авто, /гараж, /гонка)
- Crypto Exchange Suite (/крипта, /купить_крипту, /продать_крипту)
- Daily Quests Suite (/квесты)
- Casino Mini-games (/монетка, /кости)
"""
from __future__ import annotations

import datetime
import logging
import random
import time
from typing import Optional

import disnake
from disnake.ext import commands

import config
import db

log = logging.getLogger("moxxi-dc")


def build_bar(cur: int, total: int, length: int = 10) -> str:
    ratio = min(1.0, max(0.0, cur / total if total > 0 else 0))
    filled = int(length * ratio)
    return "▰" * filled + "▱" * (length - filled)


class SlashExtra(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ═══════════════════════════════════════════════════════════════
    # 1. 🐾 ПИТОМЦЫ И ЭКСПЕДИЦИИ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="питомец", description="🐾 Информация о вашем верном питомце, экспедициях и прокачке")
    async def cmd_pet(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        pet = await db.get_user_pet(u_uid)

        if not pet:
            embed = disnake.Embed(
                title="🐾 ПИТОМНИК MOXXI",
                description=(
                    "У вас пока ещё нет питомца!\n\n"
                    "Заведите себе преданного друга, который будет приносить вам сокровища и опыт из походов:\n\n"
                    "• 🐱 **Котёнок** — `20,000` 🌑 монет\n"
                    "• 🐶 **Хаски** — `45,000` 🌑 монет\n"
                    "• 🦊 **Лисичка** — `120,000` 🌑 монет\n"
                    "• 🐲 **Дракончик** — `600,000` 🌑 монет\n\n"
                    "👉 *Приручить питомца:* `/приручить` или `приручить котёнок Барсик`"
                ),
                color=disnake.Color.blurple()
            )
            return await inter.edit_original_response(embed=embed)

        p_type = pet.get("pet_type", "cat")
        p_name = pet.get("pet_name", "Питомец")
        lvl = pet.get("level", 1) or 1
        xp = pet.get("xp", 0) or 0
        hunger = pet.get("hunger", 100) or 100
        now = int(time.time())
        exp_until = pet.get("expedition_until", 0) or 0

        # Progress bar XP
        xp_next = lvl * 100
        xp_cur = xp % xp_next
        xp_bar = build_bar(xp_cur, xp_next, 8)

        # Hunger bar
        hunger_bar = build_bar(hunger, 100, 8)

        # Expedition status
        if exp_until > now:
            status_text = f"🧭 **В экспедиции** (возврат <t:{exp_until}:R>)"
        elif exp_until > 0 and exp_until <= now:
            status_text = "🎉 **Вернулся из экспедиции!** Заберите добычу!"
        else:
            status_text = "🏡 **Отдыхает дома**"

        pet_icons = {"cat": "🐱", "dog": "🐶", "fox": "🦊", "dragon": "🐲"}
        icon = pet_icons.get(p_type, "🐾")

        embed = disnake.Embed(
            title=f"{icon} Питомец: {p_name} ({lvl} уровень)",
            description=(
                f"🌟 **Уровень:** `{lvl}`\n"
                f"⚡️ **Опыт:** `[{xp_bar}]` {xp_cur}/{xp_next} XP\n"
                f"🍖 **Сытость:** `[{hunger_bar}]` {hunger}/100%\n"
                f"📍 **Статус:** {status_text}\n\n"
                f"💡 *Отправляйте питомца в поход, чтобы получать редкие монеты и опыт!*"
            ),
            color=disnake.Color.green()
        )

        view = disnake.ui.View(timeout=None)
        view.add_item(disnake.ui.Button(label="🍖 Покормить", style=disnake.ButtonStyle.success, custom_id="dc_pet_feed"))
        view.add_item(disnake.ui.Button(label="🧭 В экспедицию", style=disnake.ButtonStyle.primary, custom_id="dc_pet_expedition"))
        view.add_item(disnake.ui.Button(label="🏆 Забрать добычу", style=disnake.ButtonStyle.secondary, custom_id="dc_pet_claim"))

        await inter.edit_original_response(embed=embed, view=view)

    @commands.slash_command(name="приручить", description="🐾 Купить и приручить нового питомца")
    async def cmd_tame_pet(
        self,
        inter: disnake.ApplicationCommandInteraction,
        тип: str = commands.Param(
            description="Выберите вид питомца",
            choices=[
                disnake.OptionChoice("🐱 Котёнок (20,000 🌑)", "cat"),
                disnake.OptionChoice("🐶 Хаски (45,000 🌑)", "dog"),
                disnake.OptionChoice("🦊 Лисичка (120,000 🌑)", "fox"),
                disnake.OptionChoice("🐲 Дракончик (600,000 🌑)", "dragon"),
            ]
        ),
        кличка: str = commands.Param(description="Придумайте кличку для вашего питомца")
    ):
        await inter.response.defer()
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        u_data = await db.get_user(u_uid) or {}
        bal = u_data.get("balance", 0)

        prices = {"cat": 20000, "dog": 45000, "fox": 120000, "dragon": 600000}
        cost = prices.get(тип, 20000)

        if bal < cost:
            return await inter.edit_original_response(f"❌ Недостаточно монет! Требуется `{cost:,}` 🌑 (у вас `{bal:,}` 🌑).")

        clean_name = кличка.strip()[:24]
        await db.add_balance(u_uid, -cost)
        await db.buy_pet(u_uid, тип, clean_name)

        names = {"cat": "Котёнок 🐱", "dog": "Хаски 🐶", "fox": "Лисичка 🦊", "dragon": "Дракончик 🐲"}
        embed = disnake.Embed(
            title="🎉 ПОЗДРАВЛЯЕМ С ПРИРУЧЕНИЕМ!",
            description=(
                f"У вас появился новый верный спутник: **{names.get(тип, 'Питомец')}** по кличке **{clean_name}**!\n\n"
                f"💰 Стоимость: `-{cost:,}` 🌑 монет.\n\n"
                f"👉 Откройте меню питомца: `/питомец`"
            ),
            color=disnake.Color.green()
        )
        await inter.edit_original_response(embed=embed)

    @commands.slash_command(name="покормить", description="🍖 Покормить своего питомца и повысить его сытость")
    async def cmd_feed_pet(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        pet = await db.get_user_pet(u_uid)
        if not pet:
            return await inter.edit_original_response("❌ У вас нет питомца! Приручите его: `/приручить`.")
        await db.feed_pet(u_uid)
        await db.progress_daily_quest(u_uid, "feed", 1)
        await inter.edit_original_response(f"🍖 Вы вкусно покормили **{pet['pet_name']}**! Сытость восстановлена до 100%, +30 XP питомца!")

    @commands.slash_command(name="экспедиция", description="🧭 Отправить питомца в 30-минутный поход за золотом и XP")
    async def cmd_pet_exp(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        ok, msg = await db.send_pet_expedition(u_uid)
        await inter.edit_original_response(msg)

    @commands.slash_command(name="забрать_добычу", description="🏆 Забрать награду питомца после возвращения из похода")
    async def cmd_pet_claim(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        ok, msg = await db.claim_pet_expedition(u_uid)
        await inter.edit_original_response(msg)

    # ═══════════════════════════════════════════════════════════════
    # 2. 🏎 АВТОСАЛОН, СУПЕРКАРЫ И ГОНКИ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="автосалон", description="🏎 Каталог спортивных автомобилей и гиперкаров")
    async def cmd_car_shop(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        embed = disnake.Embed(
            title="🏎 АВТОСАЛОН ЭЛИТНЫХ АВТОМОБИЛЕЙ MOXXI",
            description=(
                "Выберите автомобиль мечты и участвуйте в уличных гонках `/гонка`!\n\n"
                "• **1.** 🚗 **Lada Vesta Sport** — `30,000` 🌑 (180 км/ч)\n"
                "• **2.** 🚙 **BMW M5 F90 CS** — `180,000` 🌑 (305 км/ч)\n"
                "• **3.** 🏎 **Porsche 911 Turbo S** — `650,000` 🌑 (330 км/ч)\n"
                "• **4.** 🔥 **Lamborghini Aventador SVJ** — `1,800,000` 🌑 (352 км/ч)\n"
                "• **5.** 🚀 **Bugatti Chiron Super Sport** — `6,000,000` 🌑 (440 км/ч)\n\n"
                "👉 *Купить авто:* `/купить_авто` или `купить авто bmw`\n"
                "📂 *Ваш автопарк:* `/гараж`"
            ),
            color=disnake.Color.gold()
        )
        await inter.edit_original_response(embed=embed)

    @commands.slash_command(name="купить_авто", description="🚗 Купить автомобиль в свой личный гараж")
    async def cmd_buy_car(
        self,
        inter: disnake.ApplicationCommandInteraction,
        модель: str = commands.Param(
            description="Выберите модель автомобиля для покупки",
            choices=[
                disnake.OptionChoice("🚗 Lada Vesta Sport (30,000 🌑)", "vesta"),
                disnake.OptionChoice("🚙 BMW M5 F90 CS (180,000 🌑)", "bmw"),
                disnake.OptionChoice("🏎 Porsche 911 Turbo S (650,000 🌑)", "porsche"),
                disnake.OptionChoice("🔥 Lamborghini Aventador SVJ (1,800,000 🌑)", "lambo"),
                disnake.OptionChoice("🚀 Bugatti Chiron Super Sport (6,000,000 🌑)", "bugatti"),
            ]
        )
    ):
        await inter.response.defer()
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        ok, msg = await db.buy_user_car(u_uid, модель)
        await inter.edit_original_response(msg)

    @commands.slash_command(name="гараж", description="📂 Список ваших личных автомобилей и их параметры")
    async def cmd_garage(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        cars = await db.get_user_cars(u_uid)

        if not cars:
            embed = disnake.Embed(
                title="📂 ВАШ ГАРАЖ ПУСТ",
                description="У вас пока нет ни одной машины!\n\nЗагляните в автосалон: `/автосалон`.",
                color=disnake.Color.orange()
            )
            return await inter.edit_original_response(embed=embed)

        embed = disnake.Embed(
            title=f"🚘 ГАРАЖ — {inter.author.display_name} ({len(cars)} авто)",
            description="Список ваших автомобилей:\n\n",
            color=disnake.Color.blurple()
        )
        for i, c in enumerate(cars, 1):
            key = c.get("car_key", "")
            spec = db.CAR_CATALOG.get(key, {"name": f"Автомобиль ({key})", "cost": 0, "speed": 100})
            spd = spec.get("speed", 150)
            embed.add_field(
                name=f"{i}. {spec['name']}",
                value=f"⚡️ Макс. скорость: `{spd} км/ч` | 💰 Цена: `{spec['cost']:,}` 🌑",
                inline=False
            )
        embed.set_footer(text="Участвуйте в гонках: /гонка")
        await inter.edit_original_response(embed=embed)

    @commands.slash_command(name="гонка", description="🏁 Принять участие в уличной дуэли на суперкаре")
    async def cmd_race(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        cars = await db.get_user_cars(u_uid)
        if not cars:
            return await inter.edit_original_response("❌ Для гонки вам нужен автомобиль! Купите его в `/автосалон`.")

        best_car = cars[0]
        c_spec = db.CAR_CATALOG.get(best_car.get("car_key", ""), {"name": "Авто", "speed": 180})
        user_speed = c_spec.get("speed", 180) + random.randint(-15, 25)

        opp_names = ["Доминик Торетто", "Брайан О'Коннор", "Хан", "Уличный рейсер", "Ночной призрак"]
        opp = random.choice(opp_names)
        opp_speed = random.randint(160, 360)

        win = user_speed >= opp_speed
        if win:
            prize = random.randint(1200, 3500)
            await db.add_balance(u_uid, prize)
            await db.add_user_xp(u_uid, 60)
            embed = disnake.Embed(
                title="🏁 ПОБЕДА В ГОНКЕ!",
                description=(
                    f"🏎 Вы выжали максимум из **{c_spec['name']}**!\n\n"
                    f"📊 **Ваша скорость на финише:** `{user_speed} км/ч`\n"
                    f"🏎 **Соперник ({opp}):** `{opp_speed} км/ч`\n\n"
                    f"💰 **Призовые:** `+{prize:,}` 🌑 монет и `+60 XP`!"
                ),
                color=disnake.Color.green()
            )
        else:
            embed = disnake.Embed(
                title="🏁 ВТОРОЕ МЕСТО В ГОНКЕ",
                description=(
                    f"Соперник **{opp}** обошёл вас на последнем повороте!\n\n"
                    f"📊 **Ваша скорость:** `{user_speed} км/ч`\n"
                    f"🏎 **Скорость соперника:** `{opp_speed} км/ч`\n\n"
                    f"Попробуйте модернизировать авто или приобрести более мощный гиперкар в `/автосалон`!"
                ),
                color=disnake.Color.red()
            )
        await inter.edit_original_response(embed=embed)

    # ═══════════════════════════════════════════════════════════════
    # 3. 📈 КРИПТОВАЛЮТНАЯ БИРЖА (MOXXICOIN / MOX)
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="крипта", description="📈 Биржевой курс MoxxiCoin (MOX), динамика и ваш портфель")
    async def cmd_crypto(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        rate, change, last_up = await db.get_crypto_rate()
        my_mox = await db.get_user_crypto(u_uid)
        equiv = int(my_mox * rate)

        trend = f"📈 `+{change:.1f}%`" if change >= 0 else f"📉 `{change:.1f}%`"

        embed = disnake.Embed(
            title="📈 БИРЖА MOXXICOIN (MOX)",
            description=(
                f"💎 **Текущий курс:** `1 MOX = {rate:,.2f} 🌑` ({trend})\n"
                f"⏱ Курс обновляется в реальном времени каждые 3 минуты.\n\n"
                f"👛 **Ваш криптопортфель:**\n"
                f"• Баланс: **{my_mox:.4f} MOX** (~`{equiv:,}` 🌑 монет)\n\n"
                f"📌 **Торговые операции:**\n"
                f"• Купить: `/купить_крипту [кол-во]`\n"
                f"• Продать: `/продать_крипту [кол-во]`"
            ),
            color=disnake.Color.teal()
        )
        embed.set_footer(text="MOXXI Crypto Exchange • Инвестируйте с умом")
        await inter.edit_original_response(embed=embed)

    @commands.slash_command(name="купить_крипту", description="💰 Купить криптовалюту MOX за монеты")
    async def cmd_buy_crypto(
        self,
        inter: disnake.ApplicationCommandInteraction,
        кол_во: float = commands.Param(description="Количество MOX для покупки (например: 5.5)")
    ):
        await inter.response.defer()
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        ok, msg = await db.buy_crypto(u_uid, кол_во)
        await inter.edit_original_response(msg)

    @commands.slash_command(name="продать_крипту", description="💸 Продать криптовалюту MOX и забрать монеты")
    async def cmd_sell_crypto(
        self,
        inter: disnake.ApplicationCommandInteraction,
        кол_во: float = commands.Param(description="Количество MOX для продажи (например: 5.5)")
    ):
        await inter.response.defer()
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        ok, msg = await db.sell_crypto(u_uid, кол_во)
        await inter.edit_original_response(msg)

    # ═══════════════════════════════════════════════════════════════
    # 4. 📜 ЕЖЕДНЕВНЫЕ КВЕСТЫ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="квесты", description="📜 Список ваших ежедневных квестов и наград")
    async def cmd_quests(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        quests = await db.get_or_create_daily_quests(u_uid)

        embed = disnake.Embed(
            title="📜 ЕЖЕДНЕВНЫЕ ЗАДАНИЯ MOXXI",
            description="Выполняйте квесты каждый день и получайте щедрые награды!\n\n",
            color=disnake.Color.blurple()
        )

        view = disnake.ui.View(timeout=None)
        has_buttons = False

        for q in quests:
            cur = q.get("current_count", 0)
            target = q.get("target_count", 1)
            bar = build_bar(cur, target, 6)
            is_done = q.get("completed", 0) == 1
            is_claimed = q.get("claimed", 0) == 1

            if is_claimed:
                st = "✅ **Награда получена**"
            elif is_done:
                st = "🎁 **Выполнено! Нажмите кнопку ниже, чтобы забрать!**"
                view.add_item(disnake.ui.Button(
                    label=f"🎁 Забрать ({q['reward_coins']} 🌑)",
                    style=disnake.ButtonStyle.success,
                    custom_id=f"dc_quest_claim:{q['quest_id']}"
                ))
                has_buttons = True
            else:
                st = f"⏳ В процессе: `{cur}/{target}`"

            embed.add_field(
                name=f"{q['quest_title']}",
                value=f"Прогресс: `[{bar}]` ({cur}/{target})\nНаграда: `+{q['reward_coins']:,}` 🌑 | `+{q['reward_xp']}` XP\nСтатус: {st}",
                inline=False
            )

        embed.set_footer(text="Квесты обновляются каждую полночь!")
        if has_buttons:
            await inter.edit_original_response(embed=embed, view=view)
        else:
            await inter.edit_original_response(embed=embed)

    # ═══════════════════════════════════════════════════════════════
    # 5. 🎲 КАЗИНО: МОНЕТКА И КОСТИ
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="монетка", description="🪙 Подбросить монетку: Орёл или Решка")
    async def cmd_coinflip(
        self,
        inter: disnake.ApplicationCommandInteraction,
        ставка: int = commands.Param(description="Сумма ставки в монетах"),
        выбор: str = commands.Param(
            description="Орёл или Решка",
            choices=[
                disnake.OptionChoice("🦅 Орёл", "орёл"),
                disnake.OptionChoice("🪙 Решка", "решка")
            ]
        )
    ):
        await inter.response.defer()
        if ставка <= 0:
            return await inter.edit_original_response("❌ Ставка должна быть больше 0!")
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        u_data = await db.get_user(u_uid) or {}
        bal = u_data.get("balance", 0)

        if bal < ставка:
            return await inter.edit_original_response(f"❌ Недостаточно средств! Баланс: `{bal:,}` 🌑.")

        coin_res = random.choice(["орёл", "решка"])
        won = coin_res == выбор.lower()

        if won:
            await db.add_balance(u_uid, ставка)
            await db.progress_daily_quest(u_uid, "slots", 1)
            embed = disnake.Embed(
                title=f"🪙 МОНЕТКА: ВЫПАЛ {coin_res.upper()}!",
                description=f"🎉 **Поздравляем!** Вы угадали и выиграли `+{ставка:,}` 🌑 монет!",
                color=disnake.Color.green()
            )
        else:
            await db.add_balance(u_uid, -ставка)
            await db.progress_daily_quest(u_uid, "slots", 1)
            embed = disnake.Embed(
                title=f"🪙 МОНЕТКА: ВЫПАЛ {coin_res.upper()}!",
                description=f"😢 К сожалению, вы не угадали. Проигрыш: `-{ставка:,}` 🌑 монет.",
                color=disnake.Color.red()
            )
        await inter.edit_original_response(embed=embed)

    @commands.slash_command(name="кости", description="🎲 Сыграть в кости против бота MOXXI")
    async def cmd_dice(
        self,
        inter: disnake.ApplicationCommandInteraction,
        ставка: int = commands.Param(description="Сумма ставки в монетах")
    ):
        await inter.response.defer()
        if ставка <= 0:
            return await inter.edit_original_response("❌ Ставка должна быть больше 0!")
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        u_data = await db.get_user(u_uid) or {}
        bal = u_data.get("balance", 0)

        if bal < ставка:
            return await inter.edit_original_response(f"❌ Недостаточно средств! Баланс: `{bal:,}` 🌑.")

        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        b1, b2 = random.randint(1, 6), random.randint(1, 6)
        u_sum = d1 + d2
        b_sum = b1 + b2

        if u_sum > b_sum:
            await db.add_balance(u_uid, ставка)
            await db.progress_daily_quest(u_uid, "slots", 1)
            embed = disnake.Embed(
                title="🎲 КОСТИ: ВЫ ПОБЕДИЛИ!",
                description=(
                    f"👤 **Ваш бросок:** 🎲 {d1} + 🎲 {d2} = **{u_sum}**\n"
                    f"🤖 **Бросок MOXXI:** 🎲 {b1} + 🎲 {b2} = **{b_sum}**\n\n"
                    f"🎉 Выигрыш: `+{ставка:,}` 🌑 монет!"
                ),
                color=disnake.Color.green()
            )
        elif u_sum < b_sum:
            await db.add_balance(u_uid, -ставка)
            await db.progress_daily_quest(u_uid, "slots", 1)
            embed = disnake.Embed(
                title="🎲 КОСТИ: ВЫ ПРОИГРАЛИ",
                description=(
                    f"👤 **Ваш бросок:** 🎲 {d1} + 🎲 {d2} = **{u_sum}**\n"
                    f"🤖 **Бросок MOXXI:** 🎲 {b1} + 🎲 {b2} = **{b_sum}**\n\n"
                    f"😢 Потеряно: `-{ставка:,}` 🌑 монет."
                ),
                color=disnake.Color.red()
            )
        else:
            embed = disnake.Embed(
                title="🎲 КОСТИ: НИЧЬЯ!",
                description=(
                    f"👤 **Ваш бросок:** 🎲 {d1} + 🎲 {d2} = **{u_sum}**\n"
                    f"🤖 **Бросок MOXXI:** 🎲 {b1} + 🎲 {b2} = **{b_sum}**\n\n"
                    f"🤝 Ставка возвращена на ваш баланс!"
                ),
                color=disnake.Color.gold()
            )
        await inter.edit_original_response(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(SlashExtra(bot))
