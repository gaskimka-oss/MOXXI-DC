# -*- coding: utf-8 -*-
"""Модуль поддержки через Личные Сообщения (ЛС / Direct Messages) с ботом MOXXI (ModMail).
Позволяет любому пользователю Discord:
- Общаться с разработчиками MOXXI напрямую через ЛС бота;
- Использовать интерактивные кнопки для подачи тикетов, баг-репортов и предложений;
- Получать официальные ответы от создателей бота прямо в свой диалог.
"""
from __future__ import annotations

import datetime
import html
import logging
import os
import time
from typing import Optional

import disnake
from disnake.ext import commands

import config
import db

log = logging.getLogger("moxxi-dc")


# ═════════════════════════════════════════════════════════════════════════════
# 📝 МОДАЛЬНОЕ ОКНО ДЛЯ ОБРАЩЕНИЯ В ЛС К РАЗРАБОТЧИКАМ
# ═════════════════════════════════════════════════════════════════════════════
class DMTicketModal(disnake.ui.Modal):
    def __init__(self, topic_type: str = "ticket"):
        self.topic_type = topic_type

        if topic_type == "bug":
            title = "🐛 Сообщить о баге в боте MOXXI"
            topic_label = "Краткая суть ошибки или бага"
            topic_ph = "Например: не работает кнопка в слотах, зависает команда..."
            desc_label = "Подробное описание и шаги для повторения"
            desc_ph = "Опишите, какую команду вводили и что произошло..."
        elif topic_type == "idea":
            title = "💡 Предложить идею для бота MOXXI"
            topic_label = "Суть вашей идеи"
            topic_ph = "Например: добавить клановые сундуки, новые работы..."
            desc_label = "Подробное описание предложения"
            desc_ph = "Как именно это должно работать и почему будет интересно..."
        else:
            title = "🛠 Вопрос разработчикам MOXXI"
            topic_label = "Тема вашего обращения"
            topic_ph = "Вопрос по настройке, сотрудничество, донат бота..."
            desc_label = "Подробный текст сообщения"
            desc_ph = "Напишите все подробности вашего вопроса..."

        components = [
            disnake.ui.TextInput(
                label=topic_label[:45],
                placeholder=topic_ph[:100],
                custom_id="dm_topic",
                style=disnake.TextInputStyle.short,
                max_length=100,
                required=True,
            ),
            disnake.ui.TextInput(
                label=desc_label[:45],
                placeholder=desc_ph[:100],
                custom_id="dm_description",
                style=disnake.TextInputStyle.paragraph,
                max_length=1000,
                required=True,
            ),
            disnake.ui.TextInput(
                label="Ссылка на скриншот (необязательно)"[:45],
                placeholder="Imgur, Discord, YouTube, Pastebin...",
                custom_id="dm_proof",
                style=disnake.TextInputStyle.short,
                max_length=200,
                required=False,
            ),
        ]
        super().__init__(
            title=title[:45],
            custom_id=f"moxxi_modal_dm:{topic_type}",
            components=components,
        )

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)

        topic = inter.text_values.get("dm_topic", "").strip()
        description = inter.text_values.get("dm_description", "").strip()
        proof = inter.text_values.get("dm_proof", "").strip()

        full_text = f"Тема: {topic}\n\nОписание:\n{description}"
        if proof:
            full_text += f"\n\nДоказательства / Ссылки:\n{proof}"

        # 1. Записываем тикет в глобальную базу support_tickets
        tid = await db.create_support_ticket(
            user_id=config.DISCORD_UID_OFFSET + inter.author.id,
            user_name=str(inter.author),
            text=full_text,
            status="open",
            platform="discord_dm",
            platform_peer_id=inter.channel_id or 0
        )

        # 2. Отвечаем пользователю в ЛС с подтверждением
        type_titles = {
            "bug": "🐛 Сообщение об ошибке",
            "idea": "💡 Предложение по боту",
            "ticket": "🛠 Обращение в техподдержку",
        }
        tag = type_titles.get(self.topic_type, "🛠 Обращение")

        confirm_embed = disnake.Embed(
            title=f"✅ {tag} #{tid} успешно отправлено!",
            description=(
                f"Спасибо за ваше обращение, **{inter.author.display_name}**!\n\n"
                f"📋 **Тема:** `{topic}`\n"
                f"⏱ **Статус:** 🟢 `Передано разработчикам MOXXI`\n\n"
                f"💬 **Как вы получите ответ?**\n"
                f"Как только разработчик ответит на ваше обращение, бот **MOXXI** пришлёт ответ "
                f"прямо сюда в этот диалог с полным текстом решения!"
            ),
            color=disnake.Color.green()
        )
        confirm_embed.set_footer(text="MOXXI Support Team • ID обращения: #" + str(tid))
        await inter.edit_original_response(embed=confirm_embed)

        # 3. Маршрутизация разработчикам (Оповещение в канал поддержки или владельцу)
        await notify_developers_about_ticket(inter.bot, tid, inter.author, self.topic_type, topic, description, proof)


# ═════════════════════════════════════════════════════════════════════════════
# 📢 ОПОВЕЩЕНИЕ РАЗРАБОТЧИКОВ О НОВОМ ТИКЕТЕ
# ═════════════════════════════════════════════════════════════════════════════
async def notify_developers_about_ticket(
    bot: commands.Bot,
    ticket_id: int,
    author: disnake.User | disnake.Member,
    topic_type: str,
    topic: str,
    description: str,
    proof: str = ""
):
    type_meta = {
        "bug": ("🐛 БАГ-РЕПОРТ", disnake.Color.red()),
        "idea": ("💡 ИДЕЯ / ПРЕДЛОЖЕНИЕ", disnake.Color.gold()),
        "ticket": ("🛠 ОБРАЩЕНИЕ К РАЗРАБОТЧИКАМ", disnake.Color.blurple()),
    }
    header, color = type_meta.get(topic_type, ("🛠 ОБРАЩЕНИЕ", disnake.Color.blurple()))

    embed = disnake.Embed(
        title=f"🆘 {header} #{ticket_id}",
        description=(
            f"👤 **От пользователя:** {author.mention} (`{author}` | ID: `{author.id}`)\n"
            f"📅 **Время:** <t:{int(time.time())}:F>\n\n"
            f"📌 **Тема:**\n```\n{topic}\n```\n"
            f"📝 **Текст сообщения:**\n```\n{description}\n```"
        ),
        color=color
    )
    if proof:
        embed.add_field(name="🔗 Ссылки / Вложения", value=proof, inline=False)

    if author.display_avatar:
        embed.set_thumbnail(url=author.display_avatar.url)

    embed.set_footer(text=f"MOXXI Developer Desk • Тикет #{ticket_id}")

    # Кнопки для разработчиков прямо под сообщением:
    # dc_t_claim (взять), dc_t_answer (ответить модалкой), dc_t_reject (отклонить)
    view = disnake.ui.View(timeout=None)
    view.add_item(disnake.ui.Button(
        label="💬 Взять в работу",
        style=disnake.ButtonStyle.success,
        custom_id=f"dc_t_claim:{ticket_id}",
        emoji="✋"
    ))
    view.add_item(disnake.ui.Button(
        label="✍️ Ответить пользователю",
        style=disnake.ButtonStyle.primary,
        custom_id=f"dc_t_answer:{ticket_id}",
        emoji="📩"
    ))
    view.add_item(disnake.ui.Button(
        label="🔒 Закрыть тикет",
        style=disnake.ButtonStyle.danger,
        custom_id=f"dc_t_reject:{ticket_id}",
        emoji="🚫"
    ))

    # 1. Проверяем настроенный канал разработчиков
    channel_id_env = os.getenv("DISCORD_DEV_CHANNEL_ID") or os.getenv("DISCORD_SUPPORT_CHANNEL_ID") or ""
    dev_channel = None
    if channel_id_env and channel_id_env.isdigit():
        dev_channel = bot.get_channel(int(channel_id_env))

    # 2. Если отдельный канал не настроен, ищем владельца бота (Application Owner)
    sent = False
    if dev_channel and isinstance(dev_channel, disnake.TextChannel):
        try:
            await dev_channel.send(embed=embed, view=view)
            sent = True
        except Exception as e:
            log.warning("Could not send ticket to dev channel: %s", e)

    if not sent:
        try:
            app_info = await bot.application_info()
            owner = app_info.owner
            if owner:
                await owner.send(
                    content=f"🔔 **Новое обращение в ЛС бота MOXXI от {author.display_name}!**",
                    embed=embed,
                    view=view
                )
        except Exception as e:
            log.warning("Could not notify bot owner about ticket: %s", e)


INVITE_URL = getattr(
    config,
    "INVITE_URL",
    "https://discord.com/api/oauth2/authorize?client_id=1568910980002619402&permissions=8&scope=bot%20applications.commands"
)


# ═════════════════════════════════════════════════════════════════════════════
# 🎮 ГЛАВНАЯ ПАНЕЛЬ С КНОПКАМИ ДЛЯ ЛИЧНЫХ СООБЩЕНИЙ (DM Hub View)
# ═════════════════════════════════════════════════════════════════════════════
class DMSupportHubView(disnake.ui.View):
    def __init__(self, user_name: str = "Игрок", balance: int = 1000, user_id: int = 0):
        super().__init__(timeout=None)

        import urllib.parse
        safe_name = urllib.parse.quote(str(user_name or "Игрок"))
        webapp_url = f"https://gaskimka-oss.github.io/MOXXI/?user={safe_name}&balance={balance}&platform=discord&uid={user_id}"

        # РЯД 0: Быстрый доступ и старт
        self.add_item(disnake.ui.Button(
            label="🚀 Главное меню (Старт)",
            style=disnake.ButtonStyle.success,
            custom_id="moxxi_dm_start_btn",
            emoji="🚀",
            row=0
        ))
        self.add_item(disnake.ui.Button(
            label="🎮 Открыть WebApp",
            url=webapp_url,
            style=disnake.ButtonStyle.link,
            emoji="🕹",
            row=0
        ))
        self.add_item(disnake.ui.Button(
            label="➕ Добавить бота",
            url=INVITE_URL,
            style=disnake.ButtonStyle.link,
            emoji="🤖",
            row=0
        ))

        # РЯД 1: Меню команд и поддержка
        self.add_item(disnake.ui.Button(
            label="📖 Меню команд",
            style=disnake.ButtonStyle.secondary,
            custom_id="moxxi_dm_help_btn",
            emoji="📜",
            row=1
        ))
        self.add_item(disnake.ui.Button(
            label="🛠 Написать разработчикам",
            style=disnake.ButtonStyle.primary,
            custom_id="moxxi_dm_ticket_btn",
            emoji="💬",
            row=1
        ))
        self.add_item(disnake.ui.Button(
            label="🐛 Сообщить о баге",
            style=disnake.ButtonStyle.danger,
            custom_id="moxxi_dm_bug_btn",
            emoji="🐞",
            row=1
        ))

        # РЯД 2: Дополнительно
        self.add_item(disnake.ui.Button(
            label="💡 Предложить идею",
            style=disnake.ButtonStyle.secondary,
            custom_id="moxxi_dm_idea_btn",
            emoji="✨",
            row=2
        ))


# ═════════════════════════════════════════════════════════════════════════════
# ⚡️ ОБРАБОТЧИК КЛИКОВ КНОПОК В ЛС
# ═════════════════════════════════════════════════════════════════════════════
async def handle_dm_button_interaction(inter: disnake.MessageInteraction) -> bool:
    cid = inter.component.custom_id
    if not cid:
        return False

    if cid == "moxxi_dm_start_btn":
        u_uid = config.DISCORD_UID_OFFSET + inter.author.id
        await db.ensure_user(u_uid, username=str(inter.author), first_name=inter.author.display_name)
        u_data = await db.get_user(u_uid) or {}
        bal = u_data.get("balance", 1000)
        bank = u_data.get("bank", 0)
        level = u_data.get("level", 1)
        xp = u_data.get("xp", 0)
        rank = u_data.get("rank", 1)

        import urllib.parse
        safe_name = urllib.parse.quote(str(inter.author.display_name or "Игрок"))
        webapp_url = f"https://gaskimka-oss.github.io/MOXXI/?user={safe_name}&balance={bal}&platform=discord&uid={inter.author.id}"

        embed = disnake.Embed(
            title="🚀 ГЛАВНОЕ МЕНЮ MOXXI",
            description=(
                f"👋 Привет, {inter.author.mention}! Добро пожаловать в центр управления **MOXXI**.\n\n"
                f"💰 **На руках:** `{bal:,}` 🌑 монет | 🏦 **В банке:** `{bank:,}` 🌑\n"
                f"🎖 **Ранг:** `{rank} ур.` | ⭐ **Уровень:** `{level}` (`{xp:,}` XP)\n\n"
                f"🎮 **Быстрые действия (нажимайте кнопки ниже):**\n"
                f"• **🎮 Открыть WebApp** — кликер монет, слоты и пассивный доход\n"
                f"• **➕ Добавить бота** — пригласить MOXXI на сервер или в группу\n"
                f"• **📖 Меню команд** — полный список всех 415+ слэш-команд\n"
                f"• **🛠 Связь** — поддержка и прямое общение с разработчиками"
            ),
            color=disnake.Color.from_rgb(0, 242, 254)
        )
        if inter.author.display_avatar:
            embed.set_thumbnail(url=inter.author.display_avatar.url)
        embed.set_footer(text="MOXXI 3.0 • Нажимайте кнопки — вводить команды текстом не нужно!")

        view = disnake.ui.View(timeout=None)
        view.add_item(disnake.ui.Button(label="🎮 Открыть WebApp", url=webapp_url, style=disnake.ButtonStyle.link, emoji="🕹", row=0))
        view.add_item(disnake.ui.Button(label="➕ Добавить бота", url=INVITE_URL, style=disnake.ButtonStyle.link, emoji="🤖", row=0))
        view.add_item(disnake.ui.Button(label="🔄 Обновить меню", style=disnake.ButtonStyle.success, custom_id="moxxi_dm_start_btn", emoji="🔄", row=0))
        view.add_item(disnake.ui.Button(label="📖 Меню команд", style=disnake.ButtonStyle.secondary, custom_id="moxxi_dm_help_btn", emoji="📜", row=1))
        view.add_item(disnake.ui.Button(label="🛠 Техподдержка", style=disnake.ButtonStyle.primary, custom_id="moxxi_dm_ticket_btn", emoji="💬", row=1))

        # Если сообщение уже было главным меню — редактируем его на месте, иначе отправляем новое
        if inter.message and inter.message.author.id == inter.bot.user.id and "ГЛАВНОЕ МЕНЮ MOXXI" in (inter.message.embeds[0].title if inter.message.embeds else ""):
            await inter.response.edit_message(embed=embed, view=view)
        else:
            await inter.response.send_message(embed=embed, view=view, ephemeral=True)
        return True

    elif cid == "moxxi_dm_ticket_btn":
        await inter.response.send_modal(DMTicketModal("ticket"))
        return True

    elif cid == "moxxi_dm_bug_btn":
        await inter.response.send_modal(DMTicketModal("bug"))
        return True

    elif cid == "moxxi_dm_idea_btn":
        await inter.response.send_modal(DMTicketModal("idea"))
        return True

    elif cid == "moxxi_dm_help_btn":
        from main import HelpView
        embed = disnake.Embed(
            title="📖 НАВИГАТОР КОМАНД MOXXI (12 РАЗДЕЛОВ)",
            description=(
                "В боте **MOXXI** доступно свыше **415+ команд** и 18 игровых систем!\n\n"
                "👇 **Выберите категорию в выпадающем списке ниже**, "
                "чтобы сразу открыть полный список команд с описанием и синтаксисом:\n\n"
                "• 👑 **Раздел 1:** Администрация и ранги (1-10)\n"
                "• 🛡 **Раздел 2:** Баны, муты, варны и антирейд\n"
                "• ⚙️ **Раздел 3:** Настройки, чистка чата и фильтры\n"
                "• 💰 **Раздел 4:** Экономика, баланс, банк 5% и переводы\n"
                "• 🏢 **Раздел 5:** Бизнесы (40 шт), работы, дома, авто\n"
                "• 🎰 **Раздел 6:** Казино, 21 Очко, Слоты, Краш, Рулетка\n"
                "• ⚔️ **Раздел 7:** Данжи, шахта, рыбалка, кейсы и лут\n"
                "• 📜 **Раздел 8:** Квесты, ачивки, титулы и VIP\n"
                "• 🐉 **Раздел 9:** Кланы, Рейдовые Боссы 50 000 HP, торги\n"
                "• 💍 **Раздел 10:** Семьи, браки, дети и разводы\n"
                "• 🎭 **Раздел 11:** РП-команды (32 шт) и анимации\n"
                "• 🚔 **Раздел 12:** Город, полиция, тюрьма и ограбления"
            ),
            color=disnake.Color.from_rgb(155, 89, 182)
        )
        embed.set_footer(text="MOXXI 3.0 • Выберите категорию в списке ниже:")
        await inter.response.send_message(embed=embed, view=HelpView(), ephemeral=True)
        return True

    return False


# ═════════════════════════════════════════════════════════════════════════════
# 💬 ОБРАБОТКА ВХОДЯЩИХ СООБЩЕНИЙ В ЛС БОТА
# ═════════════════════════════════════════════════════════════════════════════
async def handle_direct_message(bot: commands.Bot, message: disnake.Message) -> None:
    """Вызывается, когда пользователь пишет боту в личные сообщения (message.guild is None)."""
    user_id = message.author.id
    u_uid = config.DISCORD_UID_OFFSET + user_id
    await db.ensure_user(u_uid, username=str(message.author), first_name=message.author.display_name)
    u_data = await db.get_user(u_uid) or {}
    bal = u_data.get("balance", 1000)

    clean = message.content.strip()

    # Формируем приветственный хаб с интерактивными кнопками
    embed = disnake.Embed(
        title="🤖 ЦЕНТР ПОДДЕРЖКИ & НАВИГАЦИИ MOXXI",
        description=(
            f"👋 Здравствуйте, **{message.author.display_name}**!\n\n"
            f"Вы находитесь в официальном диалоге с ботом **MOXXI**.\n"
            f"Здесь вы можете открыть интерактивное меню, добавить бота на сервер, "
            f"связаться с разработчиками или запустить мини-приложение!\n\n"
            f"👇 **Выберите нужное действие с помощью кнопок ниже:**"
        ),
        color=disnake.Color.from_rgb(0, 242, 254)
    )
    embed.add_field(
        name="🚀 Меню и Старт",
        value="Нажмите кнопку **«🚀 Главное меню (Старт)»**, чтобы управлять ботом в один клик без ввода команд!",
        inline=False
    )
    embed.add_field(
        name="➕ Добавить бота",
        value="Нажмите **«➕ Добавить бота»**, чтобы пригласить MOXXI на сервер или в группу",
        inline=True
    )
    embed.add_field(
        name="🎮 Игры и WebApp",
        value=f"Баланс: `{bal:,}` 🌑 монет (кликер, слоты)",
        inline=True
    )
    embed.add_field(
        name="🛠 Разработчикам",
        value="Задать вопрос, тикет, сообщить о баге или предложить идею",
        inline=True
    )

    if bot.user.display_avatar:
        embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_footer(text="MOXXI Direct Support • Все обращения обрабатываются разработчиками")

    hub_view = DMSupportHubView(
        user_name=message.author.display_name,
        balance=bal,
        user_id=message.author.id
    )

    await message.reply(embed=embed, view=hub_view)


# ═════════════════════════════════════════════════════════════════════════════
# 👑 СЛЭШ-КОМАНДЫ ДЛЯ СВЯЗИ С РАЗРАБОТЧИКАМИ СО ВСЕХ СЕРВЕРОВ
# ═════════════════════════════════════════════════════════════════════════════
class DMSupportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="пригласить",
        description="➕ Ссылка для добавления бота MOXXI в группу или на сервер"
    )
    async def cmd_moxxi_invite(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(
            title="✨ ДОБАВИТЬ MOXXI В ГРУППУ / НА СЕРВЕР ✨",
            description=(
                "👑 **MOXXI** — мощнейший многофункциональный бот нового поколения!\n\n"
                "🚀 Чтобы добавить бота на свой сервер или в группу, нажмите кнопку ниже:\n"
                f"[🔗 **Нажмите здесь для добавления бота**]({INVITE_URL})"
            ),
            color=disnake.Color.from_rgb(0, 242, 254)
        )
        view = disnake.ui.View()
        view.add_item(disnake.ui.Button(
            label="➕ Добавить в группу / на сервер",
            url=INVITE_URL,
            style=disnake.ButtonStyle.link,
            emoji="🤖"
        ))
        await inter.response.send_message(embed=embed, view=view)

    @commands.slash_command(
        name="поддержка_moxxi",
        description="🛠 Связаться напрямую с командой разработчиков бота MOXXI"
    )
    async def cmd_moxxi_support(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_modal(DMTicketModal("ticket"))

    @commands.slash_command(
        name="баг_бота",
        description="🐛 Сообщить разработчикам о найденном баге или ошибке в боте MOXXI"
    )
    async def cmd_moxxi_bug(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_modal(DMTicketModal("bug"))

    @commands.slash_command(
        name="идея_для_бота",
        description="💡 Отправить разработчикам предложение по улучшению бота MOXXI"
    )
    async def cmd_moxxi_idea(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_modal(DMTicketModal("idea"))


def setup(bot: commands.Bot):
    bot.add_cog(DMSupportCog(bot))
