# -*- coding: utf-8 -*-
"""Профессиональная система приватных каналов-тикетов для Discord бота MOXXI 3.0.
Каждый тикет создаёт отдельный скрытый текстовый канал, доступный только автору и модераторам.
Включает:
- Выпадающее меню тем (Заявки в команду/модераторы, Жалобы на читеров, Донат, Техподдержка, Общие вопросы)
- Динамические модальные окна (Modals) с анкетами под каждую категорию
- Управление тикетом внутри канала: Взять в работу (Claim), Закрыть, Скачать транскрипт диалога (.txt)
- Полная интеграция с базой данных и авто-сохранение логов
"""
from __future__ import annotations

import asyncio
import datetime
import io
import json
import logging
import time
from typing import Optional

import disnake
from disnake.ext import commands

import config
import db

log = logging.getLogger("moxxi-dc")

# ═════════════════════════════════════════════════════════════════════════════
# 📋 КАТАЛОГ КАТЕГОРИЙ ТИКЕТОВ И ПОЛЕЙ МОДАЛЬНЫХ АНКЕТ
# ═════════════════════════════════════════════════════════════════════════════
TICKET_CATEGORIES = {
    "staff": {
        "title": "🛡 Заявка в команду (Хелпер / Модератор)",
        "short_title": "Заявка в команду",
        "description": "Подать анкету на вступление в команду модерации сервера",
        "emoji": "🛡",
        "color": disnake.Color.from_rgb(0, 230, 118),
        "prefix": "заявка",
        "fields": [
            {
                "id": "nick_age",
                "label": "Ваш ник и реальный возраст",
                "placeholder": "Пример: Steve (17 лет, МСК)",
                "max_length": 60,
                "required": True,
            },
            {
                "id": "role_target",
                "label": "Желаемая должность",
                "placeholder": "Хелпер, Модератор, Технический администратор",
                "max_length": 50,
                "required": True,
            },
            {
                "id": "experience",
                "label": "Опыт работы на других серверах",
                "placeholder": "Были ли модератором, проекты, причины ухода...",
                "style": disnake.TextInputStyle.paragraph,
                "max_length": 500,
                "required": True,
            },
            {
                "id": "online_hours",
                "label": "Сколько часов в день готовы уделять?",
                "placeholder": "Пример: 3-5 часов в день, в основном вечером",
                "max_length": 100,
                "required": True,
            },
            {
                "id": "about_self",
                "label": "Почему именно вы должны стать частью команды?",
                "placeholder": "Расскажите о себе, ваших сильных сторонах и качествах...",
                "style": disnake.TextInputStyle.paragraph,
                "max_length": 600,
                "required": False,
            },
        ],
    },
    "report": {
        "title": "🚨 Жалоба на игрока / нарушителя",
        "short_title": "Жалоба на игрока",
        "description": "Сообщить о читерах, оскорблениях, грифе или нарушении правил",
        "emoji": "🚨",
        "color": disnake.Color.red(),
        "prefix": "жалоба",
        "fields": [
            {
                "id": "target_nick",
                "label": "Никнейм нарушителя",
                "placeholder": "Точный ник в игре или Discord тег",
                "max_length": 50,
                "required": True,
            },
            {
                "id": "rule_broken",
                "label": "Суть нарушения / пункт правил",
                "placeholder": "Использование читов, оскорбление родных, обман на ресурсы...",
                "style": disnake.TextInputStyle.paragraph,
                "max_length": 400,
                "required": True,
            },
            {
                "id": "proofs",
                "label": "Доказательства (ссылки на видео/скрины)",
                "placeholder": "Imgur, YouTube, Google Drive, Rutube...",
                "style": disnake.TextInputStyle.paragraph,
                "max_length": 500,
                "required": True,
            },
            {
                "id": "server_mode",
                "label": "Сервер / Режим / Время происшествия",
                "placeholder": "Анархия #2, Гриф #1, около 16:30 по МСК",
                "max_length": 100,
                "required": False,
            },
        ],
    },
    "donate": {
        "title": "💎 Вопрос по донату и покупкам",
        "short_title": "Донат и покупки",
        "description": "Проблемы с выдачей привилегий, оплатой или магазином",
        "emoji": "💎",
        "color": disnake.Color.purple(),
        "prefix": "донат",
        "fields": [
            {
                "id": "payer_nick",
                "label": "Ваш никнейм при оплате",
                "placeholder": "Ник в игре, на который оформляли покупку",
                "max_length": 50,
                "required": True,
            },
            {
                "id": "item_bought",
                "label": "Купленный товар или привилегия",
                "placeholder": "VIP+, Премиум, Спонсор, 5000 топазов...",
                "max_length": 100,
                "required": True,
            },
            {
                "id": "receipt_num",
                "label": "Номер платежа / транзакции / способ оплаты",
                "placeholder": "YooKassa, СБП, номер чека из банка...",
                "max_length": 200,
                "required": True,
            },
            {
                "id": "donate_problem",
                "label": "Что именно пошло не так?",
                "placeholder": "Деньги списались, но привилегия не выдалась...",
                "style": disnake.TextInputStyle.paragraph,
                "max_length": 500,
                "required": True,
            },
        ],
    },
    "tech": {
        "title": "⚙️ Техническая поддержка и баги",
        "short_title": "Техподдержка и баги",
        "description": "Ошибки клиента, вылеты, баги сервера и проблемы со входом",
        "emoji": "⚙️",
        "color": disnake.Color.blue(),
        "prefix": "баг",
        "fields": [
            {
                "id": "issue_summary",
                "label": "Краткая суть проблемы",
                "placeholder": "Не могу зайти на сервер, краш при открытии меню...",
                "max_length": 100,
                "required": True,
            },
            {
                "id": "issue_details",
                "label": "Подробное описание и шаги для повторения",
                "placeholder": "Опишите, что именно вы делали перед появлением ошибки...",
                "style": disnake.TextInputStyle.paragraph,
                "max_length": 600,
                "required": True,
            },
            {
                "id": "logs_link",
                "label": "Ссылка на краш-лог или скриншот ошибки",
                "placeholder": "Pastebin, McLogs, Imgur...",
                "max_length": 300,
                "required": False,
            },
        ],
    },
    "general": {
        "title": "📩 Общий вопрос администрации",
        "short_title": "Общий вопрос",
        "description": "Сотрудничество, предложения, разбан или общие вопросы",
        "emoji": "📩",
        "color": disnake.Color.gold(),
        "prefix": "тикет",
        "fields": [
            {
                "id": "topic",
                "label": "Тема вашего обращения",
                "placeholder": "Кратко сформулируйте тему...",
                "max_length": 100,
                "required": True,
            },
            {
                "id": "description",
                "label": "Подробное описание вопроса",
                "placeholder": "Напишите все детали, чтобы администратор сразу понял суть...",
                "style": disnake.TextInputStyle.paragraph,
                "max_length": 800,
                "required": True,
            },
        ],
    },
}


# ═════════════════════════════════════════════════════════════════════════════
# 📝 ДИНАМИЧЕСКАЯ МОДАЛЬНАЯ АНКЕТА ТИКЕТА
# ═════════════════════════════════════════════════════════════════════════════
class DynamicTicketModal(disnake.ui.Modal):
    def __init__(self, category_key: str):
        self.category_key = category_key
        cat = TICKET_CATEGORIES.get(category_key, TICKET_CATEGORIES["general"])
        self.cat_info = cat

        components = []
        for f in cat["fields"]:
            style = f.get("style", disnake.TextInputStyle.short)
            components.append(
                disnake.ui.TextInput(
                    label=f["label"][:45],
                    placeholder=f.get("placeholder", "")[:100],
                    custom_id=f["id"],
                    style=style,
                    max_length=f.get("max_length", 400),
                    required=f.get("required", True),
                )
            )

        super().__init__(
            title=cat["short_title"][:45],
            custom_id=f"moxxi_modal_ticket:{category_key}",
            components=components,
        )

    async def callback(self, inter: disnake.ModalInteraction):
        # Gather submitted answers
        user_answers = {}
        for f in self.cat_info["fields"]:
            val = inter.text_values.get(f["id"], "").strip()
            if val:
                user_answers[f["label"]] = val

        await create_private_ticket_channel(inter, self.category_key, user_answers)


# ═════════════════════════════════════════════════════════════════════════════
# 🚀 ДВИЖОК СОЗДАНИЯ ПРИВАТНОГО КАНАЛА ТИКЕТА
# ═════════════════════════════════════════════════════════════════════════════
async def create_private_ticket_channel(
    inter: disnake.ModalInteraction | disnake.MessageInteraction,
    category_key: str,
    user_answers: dict
):
    await inter.response.defer(ephemeral=True)
    guild = inter.guild
    if not guild:
        return await inter.edit_original_response(content="❌ Тикеты доступны только на серверах!")

    cat_info = TICKET_CATEGORIES.get(category_key, TICKET_CATEGORIES["general"])

    # 1. Проверяем лимит открытых тикетов от одного пользователя (макс 2)
    user_tickets = await db.get_user_open_dc_tickets(guild.id, inter.author.id)
    if len(user_tickets) >= 2:
        return await inter.edit_original_response(
            content="⚠️ У вас уже есть **2 открытых тикета** на этом сервере! Пожалуйста, дождитесь ответа или закройте предыдущие обращения."
        )

    # 2. Получаем настройки тикетов сервера
    settings = await db.get_ticket_settings(guild.id)
    category_id = settings.get("category_id", 0)
    target_category = guild.get_channel(category_id) if category_id else None

    # Если категория не найдена, ищем по имени или создаём автоматически
    if not target_category or not isinstance(target_category, disnake.CategoryChannel):
        for c in guild.categories:
            if "ТИКЕТ" in c.name.upper() or "ПОДДЕРЖК" in c.name.upper():
                target_category = c
                break

        if not target_category:
            try:
                target_category = await guild.create_category(
                    name="📨 ТИКЕТЫ MOXXI",
                    reason="Авто-создание категории тикетов MOXXI"
                )
                await db.save_ticket_settings(guild.id, category_id=target_category.id)
            except Exception as e:
                log.error(f"Failed to create category: {e}")
                target_category = None

    # 3. Определяем роли персонала поддержки
    staff_role_id = settings.get("staff_role_id", 0)
    staff_role = guild.get_role(staff_role_id) if staff_role_id else None

    # Если роль не настроена явно, ищем подходящую роль персонала
    if not staff_role:
        for r in guild.roles:
            if r.name.lower() in ("модератор", "хелпер", "support", "поддержка", "администратор", "staff", "admin"):
                staff_role = r
                break

    # 4. Инкрементируем номер тикета
    ticket_num = await db.increment_ticket_counter(guild.id)
    num_str = f"{ticket_num:04d}"
    chan_name = f"{cat_info['prefix']}-{num_str}"

    # 5. Настраиваем права доступа (PermissionOverwrites)
    # @everyone - ничего не видит и не пишет
    # Автор тикета - видит, пишет, отправляет файлы
    # Бот MOXXI - полные права
    # Персонал поддержки - видят, пишут, читают историю, управляют сообщениями
    overwrites = {
        guild.default_role: disnake.PermissionOverwrite(
            view_channel=False,
            send_messages=False,
            read_message_history=False
        ),
        inter.author: disnake.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            attach_files=True,
            embed_links=True,
            read_message_history=True
        ),
        guild.me: disnake.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            manage_permissions=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            manage_messages=True
        ),
    }

    if staff_role:
        overwrites[staff_role] = disnake.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            attach_files=True,
            embed_links=True,
            read_message_history=True,
            manage_messages=True
        )

    # 6. Создаем текстовый канал
    try:
        topic_text = f"Тикет #{num_str} | {cat_info['short_title']} | Создатель: {inter.author} (ID: {inter.author.id})"
        channel = await guild.create_text_channel(
            name=chan_name,
            category=target_category,
            overwrites=overwrites,
            topic=topic_text,
            reason=f"Тикет #{num_str} для {inter.author}"
        )
    except disnake.Forbidden:
        return await inter.edit_original_response(
            content="❌ У бота недостаточно прав для создания каналов! Выдайте боту MOXXI право **Manage Channels (Управлять каналами)**."
        )
    except Exception as e:
        return await inter.edit_original_response(content=f"❌ Ошибка создания канала тикета: {e}")

    # 7. Записываем тикет в базу данных
    ticket_id = await db.create_dc_ticket(
        guild_id=guild.id,
        channel_id=channel.id,
        user_id=inter.author.id,
        user_name=str(inter.author),
        category_key=category_key,
        category_title=cat_info["title"],
        form_data=user_answers
    )

    # 8. Формируем приветственное сообщение в канале тикета
    staff_mention_str = staff_role.mention if staff_role else "Команда модерации"
    welcome_text = (
        f"👋 Здравствуйте, {inter.author.mention}!\n\n"
        f"Ваше обращение принято. Сотрудники ({staff_mention_str}) скоро подключатся к диалогу.\n"
        f"Вы можете писать сообщения, прикреплять скриншоты и ссылки прямо в этот канал!"
    )

    embed = disnake.Embed(
        title=f"{cat_info['emoji']} {cat_info['title']} #{num_str}",
        description=f"👤 **Создатель:** {inter.author.mention} (`{inter.author}`)\n📅 **Дата открытия:** <t:{int(time.time())}:F>\n⏳ **Статус:** `Ожидает ответа персонала`\n",
        color=cat_info["color"]
    )
    if inter.author.display_avatar:
        embed.set_thumbnail(url=inter.author.display_avatar.url)

    # Добавляем все заполненные поля из анкеты
    for field_name, field_val in user_answers.items():
        embed.add_field(name=f"📌 {field_name}", value=f"```\n{field_val}\n```", inline=False)

    embed.set_footer(text=f"MOXXI Support System • ID обращения: #{ticket_id}")

    # Прикрепляем кнопки управления каналом
    control_view = TicketChannelControlView(ticket_id=ticket_id, claimed_by=0)

    try:
        await channel.send(
            content=f"{inter.author.mention} | {staff_role.mention if staff_role else '@here'}",
            embed=embed,
            view=control_view
        )
    except Exception as e:
        log.error(f"Failed to post welcome embed in ticket #{ticket_id}: {e}")

    # 9. Уведомляем игрока об успешном создании
    await inter.edit_original_response(
        content=f"🎉 **Ваш личный тикет успешно создан:** {channel.mention}!\nПерейдите в канал, чтобы продолжить диалог с поддержкой."
    )


# ═════════════════════════════════════════════════════════════════════════════
# 🎮 ИНТЕРФЕЙС УПРАВЛЕНИЯ ВНУТРИ КАНАЛА ТИКЕТА (Control View)
# ═════════════════════════════════════════════════════════════════════════════
class TicketChannelControlView(disnake.ui.View):
    def __init__(self, ticket_id: int, claimed_by: int = 0, claimed_name: str = ""):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        self.claimed_by = claimed_by
        self.claimed_name = claimed_name
        self._build_items()

    def _build_items(self):
        self.clear_items()

        # Кнопка закрытия
        self.add_item(disnake.ui.Button(
            label="🔒 Закрыть тикет",
            style=disnake.ButtonStyle.danger,
            custom_id=f"moxxi_tclose:{self.ticket_id}"
        ))

        # Кнопка взять в работу (Claim) / освободить
        if not self.claimed_by:
            self.add_item(disnake.ui.Button(
                label="👤 Взять в работу",
                style=disnake.ButtonStyle.success,
                custom_id=f"moxxi_tclaim:{self.ticket_id}"
            ))
        else:
            self.add_item(disnake.ui.Button(
                label=f"🔒 Взят: {self.claimed_name[:15]}",
                style=disnake.ButtonStyle.secondary,
                custom_id=f"moxxi_tbusy:{self.ticket_id}",
                disabled=True
            ))
            self.add_item(disnake.ui.Button(
                label="🔄 Освободить",
                style=disnake.ButtonStyle.secondary,
                custom_id=f"moxxi_trelease:{self.ticket_id}"
            ))

        # Кнопка транскрипта
        self.add_item(disnake.ui.Button(
            label="📄 Транскрипт",
            style=disnake.ButtonStyle.secondary,
            custom_id=f"moxxi_ttrans:{self.ticket_id}"
        ))


# ═════════════════════════════════════════════════════════════════════════════
# 📌 ИНТЕРАКТИВНОЕ МЕНЮ И КНОПКИ ГЛАВНОЙ ПАНЕЛИ ТИКЕТОВ
# ═════════════════════════════════════════════════════════════════════════════
class TicketPanelSelect(disnake.ui.Select):
    def __init__(self):
        options = [
            disnake.SelectOption(
                label="🛡 Заявка в команду (Хелпер / Модер)",
                value="staff",
                description="Подать анкету на вступление в команду сервера",
                emoji="🛡"
            ),
            disnake.SelectOption(
                label="🚨 Жалоба на игрока / нарушителя",
                value="report",
                description="Сообщить о читере, оскорблениях или грифе",
                emoji="🚨"
            ),
            disnake.SelectOption(
                label="💎 Донат и платежи",
                value="donate",
                description="Проблемы с выдачей привилегии или оплатой",
                emoji="💎"
            ),
            disnake.SelectOption(
                label="⚙️ Техподдержка и баги",
                value="tech",
                description="Ошибки клиента, вылеты, баги игрового процесса",
                emoji="⚙️"
            ),
            disnake.SelectOption(
                label="📩 Общий вопрос администрации",
                value="general",
                description="Любые другие вопросы по серверу",
                emoji="📩"
            ),
        ]
        super().__init__(
            placeholder="🔍 Выберите категорию обращения...",
            min_values=1,
            max_values=1,
            custom_id="moxxi_ticket_select",
            options=options
        )

    async def callback(self, inter: disnake.MessageInteraction):
        selected_cat = self.values[0]
        modal = DynamicTicketModal(selected_cat)
        await inter.response.send_modal(modal)


class MainTicketPanelView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketPanelSelect())

        # Дополнительные быстрые кнопки внизу выпадающего меню
        self.add_item(disnake.ui.Button(
            label="📩 Быстрый тикет",
            style=disnake.ButtonStyle.primary,
            custom_id="moxxi_ticket_quick_btn",
            emoji="🎫"
        ))
        self.add_item(disnake.ui.Button(
            label="🛡 Подать заявку в стафф",
            style=disnake.ButtonStyle.success,
            custom_id="moxxi_ticket_staff_btn",
            emoji="🛡"
        ))


# ═════════════════════════════════════════════════════════════════════════════
# 📄 ГЕНЕРАТОР ТРАНСКРИПТА ДИАЛОГА (Лог переписки в .txt)
# ═════════════════════════════════════════════════════════════════════════════
async def generate_channel_transcript(channel: disnake.TextChannel, ticket_info: dict) -> io.BytesIO:
    messages = []
    async for msg in channel.history(limit=600, oldest_first=True):
        messages.append(msg)

    buf = io.BytesIO()
    lines = [
        "=======================================================================",
        f"  ТРАНСКРИПТ ОБРАЩЕНИЯ: #{ticket_info.get('id', 0)} ({ticket_info.get('category_title', 'Тикет')})",
        f"  Сервер: {channel.guild.name} (ID: {channel.guild.id})",
        f"  Канал: #{channel.name}",
        f"  Создатель: {ticket_info.get('user_name', 'Игрок')} (ID: {ticket_info.get('user_id', 0)})",
        f"  Дата выгрузки: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=======================================================================\n\n"
    ]

    for m in messages:
        dt = m.created_at.strftime("%Y-%m-%d %H:%M:%S")
        author = f"{m.author.display_name} ({m.author})"
        content = m.clean_content or ""
        attach_str = ""
        if m.attachments:
            attach_str = " [Вложения: " + ", ".join(a.url for a in m.attachments) + "]"
        lines.append(f"[{dt}] {author}: {content}{attach_str}")

    transcript_text = "\n".join(lines)
    buf.write(transcript_text.encode("utf-8"))
    buf.seek(0)
    return buf


# ═════════════════════════════════════════════════════════════════════════════
# ⚡️ ОБРАБОТЧИК КНОПОК ТИКЕТОВ (ВЗЯТИЕ, ЗАКРЫТИЕ, ТРАНСКРИПТ)
# ═════════════════════════════════════════════════════════════════════════════
async def handle_ticket_interaction(inter: disnake.MessageInteraction) -> bool:
    cid = inter.component.custom_id
    if not cid:
        return False

    # 1. Быстрые кнопки с главной панели
    if cid == "moxxi_ticket_quick_btn":
        await inter.response.send_modal(DynamicTicketModal("general"))
        return True

    elif cid == "moxxi_ticket_staff_btn":
        await inter.response.send_modal(DynamicTicketModal("staff"))
        return True

    # 2. Действия внутри канала тикета: moxxi_tclose, moxxi_tclaim, moxxi_trelease, moxxi_ttrans
    if not (cid.startswith("moxxi_tclose:") or cid.startswith("moxxi_tclaim:") or 
            cid.startswith("moxxi_trelease:") or cid.startswith("moxxi_ttrans:") or
            cid.startswith("moxxi_tconfirm_close:")):
        return False

    parts = cid.split(":", 1)
    action = parts[0]
    tid = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

    ticket = await db.get_dc_ticket(tid) if tid else await db.get_dc_ticket_by_channel(inter.channel.id)
    if not ticket:
        await inter.response.send_message("❌ Запись тикета не найдена в базе данных!", ephemeral=True)
        return True

    guild = inter.guild
    channel = inter.channel

    # ── 1. Взять тикет в работу (Claim) ──
    if action == "moxxi_tclaim":
        await inter.response.defer()
        # Проверяем права стаффа
        is_staff = inter.author.guild_permissions.manage_messages or inter.author.guild_permissions.administrator
        settings = await db.get_ticket_settings(guild.id)
        if settings.get("staff_role_id"):
            role = guild.get_role(settings["staff_role_id"])
            if role and role in inter.author.roles:
                is_staff = True

        if not is_staff:
            return await inter.followup.send("⛔️ Брать тикеты в работу могут только сотрудники поддержки!", ephemeral=True)

        if ticket.get("claimed_by") and ticket["claimed_by"] != inter.author.id:
            c_name = ticket.get("claimed_name") or "другим модератором"
            return await inter.followup.send(f"🔒 Этот тикет уже взят в работу: **{c_name}**!", ephemeral=True)

        await db.claim_dc_ticket(tid, inter.author.id, inter.author.display_name)
        new_view = TicketChannelControlView(ticket_id=tid, claimed_by=inter.author.id, claimed_name=inter.author.display_name)

        # Обновляем embed в первом сообщении канала
        if inter.message and inter.message.embeds:
            emb = inter.message.embeds[0]
            emb.color = disnake.Color.orange()
            emb.set_footer(text=f"🔒 Взят в работу сотрудником: {inter.author.display_name}")
            await inter.message.edit(embed=emb, view=new_view)
        else:
            await inter.message.edit(view=new_view)

        await channel.send(f"👤 Сотрудник {inter.author.mention} **принял обращение в работу** и скоро ответит!")
        return True

    # ── 2. Освободить тикет (Release) ──
    elif action == "moxxi_trelease":
        await inter.response.defer()
        is_owner_or_admin = inter.author.guild_permissions.administrator or inter.author.id == guild.owner_id
        if ticket.get("claimed_by") != inter.author.id and not is_owner_or_admin:
            return await inter.followup.send("❌ Освободить тикет может только тот сотрудник, кто его взял!", ephemeral=True)

        await db.release_dc_ticket(tid)
        new_view = TicketChannelControlView(ticket_id=tid, claimed_by=0)

        if inter.message and inter.message.embeds:
            emb = inter.message.embeds[0]
            emb.color = disnake.Color.gold()
            emb.set_footer(text="🔄 Возвращён в общий пул поддержки")
            await inter.message.edit(embed=emb, view=new_view)
        else:
            await inter.message.edit(view=new_view)

        await channel.send(f"🔄 Тикет освобождён сотрудником {inter.author.mention} и возвращён в общий пул.")
        return True

    # ── 3. Запрос на закрытие тикета ──
    elif action == "moxxi_tclose":
        confirm_view = disnake.ui.View(timeout=60)
        confirm_view.add_item(disnake.ui.Button(
            label="⚠️ Подтвердить закрытие и удаление",
            style=disnake.ButtonStyle.danger,
            custom_id=f"moxxi_tconfirm_close:{tid}"
        ))
        await inter.response.send_message(
            f"Вы уверены, что хотите закрыть тикет **#{tid}**?\nДиалог будет сохранён в транскрипт, а канал удалён.",
            view=confirm_view,
            ephemeral=True
        )
        return True

    # ── 4. Подтверждение закрытия (Удаление канала и экспорт транскрипта) ──
    elif action == "moxxi_tconfirm_close":
        await inter.response.defer()
        await db.close_dc_ticket(tid, closed_by=inter.author.id, reason="Закрыто через кнопку")

        await channel.send(f"🔒 Тикет закрыт сотрудником {inter.author.mention}. Идёт сохранение транскрипта...")

        # Генерируем транскрипт диалога
        transcript_buf = await generate_channel_transcript(channel, ticket)
        filename = f"transcript-ticket-{tid}.txt"
        file_obj = disnake.File(fp=transcript_buf, filename=filename)

        # Отправляем в канал логов, если он настроен
        settings = await db.get_ticket_settings(guild.id)
        log_chan_id = settings.get("log_channel_id", 0)
        log_chan = guild.get_channel(log_chan_id) if log_chan_id else None

        if log_chan and isinstance(log_chan, disnake.TextChannel):
            try:
                log_embed = disnake.Embed(
                    title=f"📁 ТИКЕТ ЗАКРЫТ: #{tid}",
                    description=(
                        f"Категория: **{ticket.get('category_title', 'Тикет')}**\n"
                        f"Создатель: <@{ticket.get('user_id', 0)}>\n"
                        f"Закрыл: {inter.author.mention}\n"
                        f"Канал: `#{channel.name}`"
                    ),
                    color=disnake.Color.dark_grey()
                )
                await log_chan.send(embed=log_embed, file=file_obj)
            except Exception as e:
                log.error(f"Failed to post transcript to log channel: {e}")

        # Пытаемся отправить транскрипт в ЛС автору тикета
        creator_id = ticket.get("user_id")
        if creator_id:
            try:
                creator = guild.get_member(creator_id) or await guild.fetch_member(creator_id)
                if creator:
                    transcript_buf.seek(0)
                    dm_file = disnake.File(fp=transcript_buf, filename=filename)
                    await creator.send(
                        f"📬 Ваше обращение на сервере **{guild.name}** (`#{channel.name}`) было успешно закрыто сотрудником **{inter.author.display_name}**.\nПолный транскрипт диалога прикреплён к этому сообщению:",
                        file=dm_file
                    )
            except Exception:
                pass

        await channel.send("⏳ **Канал будет автоматически удалён через 5 секунд...**")
        await asyncio.sleep(5)
        try:
            await channel.delete(reason=f"Тикет #{tid} закрыт {inter.author}")
        except Exception as e:
            log.error(f"Failed to delete ticket channel: {e}")
        return True

    # ── 5. Скачать транскрипт без закрытия ──
    elif action == "moxxi_ttrans":
        await inter.response.defer(ephemeral=True)
        transcript_buf = await generate_channel_transcript(channel, ticket)
        filename = f"transcript-ticket-{tid}.txt"
        file_obj = disnake.File(fp=transcript_buf, filename=filename)
        await inter.followup.send(
            content=f"📄 **Транскрипт диалога тикета #{tid} успешно сформирован:**",
            file=file_obj,
            ephemeral=True
        )
        return True

    return False


# ═════════════════════════════════════════════════════════════════════════════
# 👑 СЛЭШ-КОМАНДЫ ДЛЯ АДМИНИСТРАТОРА И ИГРОКОВ (Tickets Cog)
# ═════════════════════════════════════════════════════════════════════════════
class TicketSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_slash_command_error(self, inter: disnake.ApplicationCommandInteraction, error: Exception):
        log.error(f"Ticket command '{inter.data.name}' failed: {error}", exc_info=True)
        msg = f"⚠️ Ошибка при выполнении команды: {error}"
        try:
            if inter.response.is_done():
                await inter.edit_original_response(content=msg)
            else:
                await inter.response.send_message(content=msg, ephemeral=True)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════
    # 1. СОЗДАТЬ ПАНЕЛЬ ТИКЕТОВ (/панель_тикетов)
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(
        name="панель_тикетов",
        description="🎫 Создать интерактивную панель поддержки и заявок на сервере"
    )
    async def cmd_create_ticket_panel(
        self,
        inter: disnake.ApplicationCommandInteraction,
        канал: Optional[disnake.TextChannel] = commands.Param(default=None, description="Канал для отправки панели (по умолчанию текущий)"),
        роль_поддержки: Optional[disnake.Role] = commands.Param(default=None, description="Роль сотрудников, которые будут отвечать на тикеты"),
        категория_тикетов: Optional[disnake.CategoryChannel] = commands.Param(default=None, description="Категория, где бот будет создавать каналы тикетов"),
        канал_логов: Optional[disnake.TextChannel] = commands.Param(default=None, description="Канал для сохранения транскриптов и закрытых тикетов"),
        заголовок: Optional[str] = commands.Param(default=None, description="Свой заголовок панели"),
        описание: Optional[str] = commands.Param(default=None, description="Свой текст описания панели"),
    ):
        if not inter.channel.permissions_for(inter.author).administrator:
            return await inter.response.send_message("❌ Только администратор сервера может создавать панель поддержки!", ephemeral=True)

        target_channel = канал or inter.channel
        guild = inter.guild

        # Сохраняем настройки в базу
        settings_update = {}
        if роль_поддержки:
            settings_update["staff_role_id"] = роль_поддержки.id
        if категория_тикетов:
            settings_update["category_id"] = категория_тикетов.id
        if канал_логов:
            settings_update["log_channel_id"] = канал_логов.id

        if settings_update:
            await db.save_ticket_settings(guild.id, **settings_update)

        title_text = заголовок or f"🎫 СЛУЖБА ПОДДЕРЖКИ • {guild.name.upper()}"
        desc_text = описание or (
            "Добро пожаловать в центр поддержки сервера!\n\n"
            "Здесь вы можете решить любые вопросы с администрацией, получить помощь по игре или донату, "
            "подать жалобу на нарушителя правил или отправить заявку в команду модерации сервера.\n\n"
            "👇 **Выберите категорию в выпадающем меню ниже**, чтобы моментально открыть ваш личный канал тикета:"
        )

        embed = disnake.Embed(
            title=title_text,
            description=desc_text,
            color=disnake.Color.from_rgb(0, 242, 254)
        )
        embed.add_field(
            name="🛡 Заявки в персонал",
            value="Хотите стать Хелпером или Модератором? Заполните удобную анкету!",
            inline=True
        )
        embed.add_field(
            name="🚨 Жалобы на игроков",
            value="Встретили читера, нарушителя или токсика? Прикрепите доказательства!",
            inline=True
        )
        embed.add_field(
            name="💎 Донат и вопросы",
            value="Проблемы с выдачей привилегий, покупками или общие предложения по серверу.",
            inline=True
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text="MOXXI Advanced Ticket System • Поддержка 24/7")

        panel_view = MainTicketPanelView()
        sent_msg = await target_channel.send(embed=embed, view=panel_view)

        await db.save_ticket_settings(
            guild.id,
            panel_channel_id=target_channel.id,
            panel_message_id=sent_msg.id
        )

        await inter.response.send_message(
            f"✅ **Панель тикетов успешно создана** в канале {target_channel.mention}!\n"
            f"• Категория для тикетов: **{категория_тикетов.name if категория_тикетов else 'Авто (📨 ТИКЕТЫ MOXXI)'}**\n"
            f"• Роль поддержки: **{роль_поддержки.mention if роль_поддержки else 'Авто-определение'}**\n"
            f"• Канал транскриптов: **{канал_логов.mention if канал_логов else 'В личные сообщения автору'}**",
            ephemeral=True
        )

    # ═══════════════════════════════════════════════════════════════
    # 2. БЫСТРЫЙ ТИКЕТ (/тикет)
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="тикет", description="📩 Моментально открыть личное обращение к администрации")
    async def cmd_user_ticket(
        self,
        inter: disnake.ApplicationCommandInteraction,
        тема: Optional[str] = commands.Param(default="Общее обращение", description="Краткая тема вашего обращения")
    ):
        await inter.response.send_modal(DynamicTicketModal("general"))

    # ═══════════════════════════════════════════════════════════════
    # 3. БЫСТРАЯ ЗАЯВКА В СТАФФ (/заявка)
    # ═══════════════════════════════════════════════════════════════
    @commands.slash_command(name="заявка", description="🛡 Подать анкету на должность в команду сервера (Хелпер / Модер)")
    async def cmd_user_staff_apply(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_modal(DynamicTicketModal("staff"))


def setup(bot: commands.Bot):
    bot.add_cog(TicketSystem(bot))
