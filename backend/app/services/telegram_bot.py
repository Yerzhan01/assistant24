from __future__ import annotations
"""Telegram bot integration using aiogram with interactive buttons."""
import logging
from typing import Any, Dict, Optional
from uuid import UUID
from datetime import datetime

from aiogram import Bot, Dispatcher, Router
from aiogram.types import (
    Message, Update, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.i18n import t
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai_router import AIRouter
from app.modules.registry import get_registry

logger = logging.getLogger(__name__)
router = Router()

# NOTE: Removed in-memory _chat_history global state (race condition risk).
# Chat history is now stored in database via ChatMessage model.
# See AIRouter.process_message() which handles history persistence.

# ==================== Button Definitions ====================

def get_main_menu_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Main menu with action buttons."""
    if lang == "kz":
        buttons = [
            [
                InlineKeyboardButton(text="📅 Кездесулер", callback_data="menu:meetings"),
                InlineKeyboardButton(text="✅ Тапсырмалар", callback_data="menu:tasks"),
            ],
            [
                InlineKeyboardButton(text="💰 Қаржы", callback_data="menu:finance"),
                InlineKeyboardButton(text="📒 Байланыстар", callback_data="menu:contacts"),
            ],
            [
                InlineKeyboardButton(text="🎂 Туған күндер", callback_data="menu:birthdays"),
                InlineKeyboardButton(text="💡 Идеялар", callback_data="menu:ideas"),
            ],
            [
                InlineKeyboardButton(text="📄 Келісім-шарттар", callback_data="menu:contracts"),
                InlineKeyboardButton(text="📊 Брифинг", callback_data="action:briefing"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Баптаулар", callback_data="menu:settings"),
                InlineKeyboardButton(text="❓ Көмек", callback_data="menu:help"),
            ],
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton(text="📅 Встречи", callback_data="menu:meetings"),
                InlineKeyboardButton(text="✅ Задачи", callback_data="menu:tasks"),
            ],
            [
                InlineKeyboardButton(text="💰 Финансы", callback_data="menu:finance"),
                InlineKeyboardButton(text="📒 Контакты", callback_data="menu:contacts"),
            ],
            [
                InlineKeyboardButton(text="🎂 Дни рождения", callback_data="menu:birthdays"),
                InlineKeyboardButton(text="💡 Идеи", callback_data="menu:ideas"),
            ],
            [
                InlineKeyboardButton(text="📄 Договоры", callback_data="menu:contracts"),
                InlineKeyboardButton(text="📊 Брифинг", callback_data="action:briefing"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
                InlineKeyboardButton(text="❓ Помощь", callback_data="menu:help"),
            ],
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_birthdays_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Birthdays submenu."""
    if lang == "kz":
        buttons = [
            [InlineKeyboardButton(text="🎉 Жақында болатын", callback_data="birthdays:upcoming")],
            [InlineKeyboardButton(text="📋 Барлық тізім", callback_data="birthdays:all")],
            [InlineKeyboardButton(text="➕ Қосу", callback_data="birthdays:new")],
            [InlineKeyboardButton(text="◀️ Артқа", callback_data="menu:main")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton(text="🎉 Ближайшие", callback_data="birthdays:upcoming")],
            [InlineKeyboardButton(text="📋 Весь список", callback_data="birthdays:all")],
            [InlineKeyboardButton(text="➕ Добавить", callback_data="birthdays:new")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_ideas_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Ideas submenu."""
    if lang == "kz":
        buttons = [
            [InlineKeyboardButton(text="✨ Жаңа идея", callback_data="ideas:new")],
            [InlineKeyboardButton(text="📋 Барлық идеялар", callback_data="ideas:all")],
            [InlineKeyboardButton(text="🔝 Маңызды", callback_data="ideas:important")],
            [InlineKeyboardButton(text="◀️ Артқа", callback_data="menu:main")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton(text="✨ Новая идея", callback_data="ideas:new")],
            [InlineKeyboardButton(text="📋 Все идеи", callback_data="ideas:all")],
            [InlineKeyboardButton(text="🔝 Важные", callback_data="ideas:important")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_contracts_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Contracts submenu."""
    if lang == "kz":
        buttons = [
            [InlineKeyboardButton(text="⏳ Мерзімі аяқталатын", callback_data="contracts:expiring")],
            [InlineKeyboardButton(text="📋 Барлық келісім-шарттар", callback_data="contracts:all")],
            [InlineKeyboardButton(text="➕ Жаңа келісім-шарт", callback_data="contracts:new")],
            [InlineKeyboardButton(text="◀️ Артқа", callback_data="menu:main")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton(text="⏳ Истекающие", callback_data="contracts:expiring")],
            [InlineKeyboardButton(text="📋 Все договоры", callback_data="contracts:all")],
            [InlineKeyboardButton(text="➕ Новый договор", callback_data="contracts:new")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_meetings_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Meetings submenu."""
    if lang == "kz":
        buttons = [
            [InlineKeyboardButton(text="📋 Бүгінгі кездесулер", callback_data="meetings:today")],
            [InlineKeyboardButton(text="📅 Апталық", callback_data="meetings:week")],
            [InlineKeyboardButton(text="➕ Жаңа кездесу", callback_data="meetings:new")],
            [InlineKeyboardButton(text="◀️ Артқа", callback_data="menu:main")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton(text="📋 Встречи сегодня", callback_data="meetings:today")],
            [InlineKeyboardButton(text="📅 На этой неделе", callback_data="meetings:week")],
            [InlineKeyboardButton(text="➕ Новая встреча", callback_data="meetings:new")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_tasks_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Tasks submenu."""
    if lang == "kz":
        buttons = [
            [InlineKeyboardButton(text="🔥 Мерзімі өткендер", callback_data="tasks:overdue")],
            [InlineKeyboardButton(text="📋 Барлық тапсырмалар", callback_data="tasks:all")],
            [InlineKeyboardButton(text="➕ Жаңа тапсырма", callback_data="tasks:new")],
            [InlineKeyboardButton(text="◀️ Артқа", callback_data="menu:main")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton(text="🔥 Просроченные", callback_data="tasks:overdue")],
            [InlineKeyboardButton(text="📋 Все задачи", callback_data="tasks:all")],
            [InlineKeyboardButton(text="➕ Новая задача", callback_data="tasks:new")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_finance_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Finance submenu."""
    if lang == "kz":
        buttons = [
            [InlineKeyboardButton(text="💸 Кіріс жазу", callback_data="finance:income")],
            [InlineKeyboardButton(text="💳 Шығыс жазу", callback_data="finance:expense")],
            [InlineKeyboardButton(text="📊 Баланс", callback_data="finance:balance")],
            [InlineKeyboardButton(text="📈 Есеп", callback_data="finance:report")],
            [InlineKeyboardButton(text="◀️ Артқа", callback_data="menu:main")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton(text="💸 Записать доход", callback_data="finance:income")],
            [InlineKeyboardButton(text="💳 Записать расход", callback_data="finance:expense")],
            [InlineKeyboardButton(text="📊 Баланс", callback_data="finance:balance")],
            [InlineKeyboardButton(text="📈 Отчёт", callback_data="finance:report")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_settings_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Settings submenu."""
    if lang == "kz":
        buttons = [
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang:kz"),
            ],
            [InlineKeyboardButton(text="🔔 Еске салулар", callback_data="settings:reminders")],
            [InlineKeyboardButton(text="◀️ Артқа", callback_data="menu:main")],
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang:kz"),
            ],
            [InlineKeyboardButton(text="🔔 Напоминания", callback_data="settings:reminders")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_contacts_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Contacts submenu."""
    if lang == "kz":
        buttons = [
            [InlineKeyboardButton(text="📋 Барлық байланыстар", callback_data="contacts:all")],
            [InlineKeyboardButton(text="🔍 Байланыс іздеу", callback_data="contacts:search")],
            [InlineKeyboardButton(text="➕ Жаңа байланыс", callback_data="contacts:new")],
            [InlineKeyboardButton(text="⭐ Жиі қолданылатын", callback_data="contacts:frequent")],
            [InlineKeyboardButton(text="◀️ Артқа", callback_data="menu:main")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton(text="📋 Все контакты", callback_data="contacts:all")],
            [InlineKeyboardButton(text="🔍 Найти контакт", callback_data="contacts:search")],
            [InlineKeyboardButton(text="➕ Новый контакт", callback_data="contacts:new")],
            [InlineKeyboardButton(text="⭐ Часто используемые", callback_data="contacts:frequent")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_reminders_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Reminders settings submenu."""
    if lang == "kz":
        buttons = [
            [
                InlineKeyboardButton(text="🌅 Таңғы брифинг", callback_data="remind:morning"),
            ],
            [
                InlineKeyboardButton(text="⏰ 08:00", callback_data="remind_time:08"),
                InlineKeyboardButton(text="⏰ 09:00", callback_data="remind_time:09"),
                InlineKeyboardButton(text="⏰ 10:00", callback_data="remind_time:10"),
            ],
            [
                InlineKeyboardButton(text="📅 Кездесу еске салу", callback_data="remind:meeting"),
            ],
            [
                InlineKeyboardButton(text="15 мин", callback_data="remind_before:15"),
                InlineKeyboardButton(text="30 мин", callback_data="remind_before:30"),
                InlineKeyboardButton(text="1 сағат", callback_data="remind_before:60"),
            ],
            [
                InlineKeyboardButton(text="✅ Дедлайн еске салу", callback_data="remind:deadline"),
            ],
            [InlineKeyboardButton(text="◀️ Артқа", callback_data="menu:settings")],
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton(text="🌅 Утренний брифинг", callback_data="remind:morning"),
            ],
            [
                InlineKeyboardButton(text="⏰ 08:00", callback_data="remind_time:08"),
                InlineKeyboardButton(text="⏰ 09:00", callback_data="remind_time:09"),
                InlineKeyboardButton(text="⏰ 10:00", callback_data="remind_time:10"),
            ],
            [
                InlineKeyboardButton(text="📅 Напоминание о встрече", callback_data="remind:meeting"),
            ],
            [
                InlineKeyboardButton(text="15 мин", callback_data="remind_before:15"),
                InlineKeyboardButton(text="30 мин", callback_data="remind_before:30"),
                InlineKeyboardButton(text="1 час", callback_data="remind_before:60"),
            ],
            [
                InlineKeyboardButton(text="✅ Напоминание о дедлайне", callback_data="remind:deadline"),
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:settings")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_contact_actions_keyboard(contact_id: str, phone:Optional[ str ], lang: str = "ru") -> InlineKeyboardMarkup:
    """Actions for a specific contact."""
    if lang == "kz":
        buttons = [
            [InlineKeyboardButton(text="📅 Кездесу жоспарлау", callback_data=f"contact_action:meet:{contact_id}")],
            [InlineKeyboardButton(text="💬 Хабарлама жазу", callback_data=f"contact_action:msg:{contact_id}")],
        ]
        if phone:
            buttons.append([InlineKeyboardButton(text=f"📞 Қоңырау шалу: {phone}", callback_data=f"contact_action:call:{contact_id}")])
        buttons.append([InlineKeyboardButton(text="◀️ Артқа", callback_data="menu:contacts")])
    else:
        buttons = [
            [InlineKeyboardButton(text="📅 Назначить встречу", callback_data=f"contact_action:meet:{contact_id}")],
            [InlineKeyboardButton(text="💬 Написать сообщение", callback_data=f"contact_action:msg:{contact_id}")],
        ]
        if phone:
            buttons.append([InlineKeyboardButton(text=f"📞 Позвонить: {phone}", callback_data=f"contact_action:call:{contact_id}")])
        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu:contacts")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)



def get_welcome_message(user_name: str, lang: str = "ru") -> str:
    """Generate welcome message."""
    if lang == "kz":
        return f"""👋 Сәлем, {user_name}!

Мен сіздің **Цифрлық Хатшыңызбын** — ИИ қуатты көмекшіңіз.

🎯 **Мен не істей аламын:**
• 📅 Кездесулер мен дедлайндарды басқару
• ✅ Тапсырмаларды бақылау
• 💰 Қаржыны есепке алу
• 🔔 Маңызды оқиғаларды еске салу
• 🧠 Контактілер туралы ақпаратты есте сақтау

💬 **Маған кез келген нәрсені жаза аласыз:**
_"Ертең Асхатпен кездесу"_
_"50 мың кіріс жаз"_
_"Бүгінге не жоспарланған?"_

👇 **Немесе батырмаларды қолданыңыз:**"""
    else:
        return f"""👋 Привет, {user_name}!

Я ваш **Цифровой Секретарь** — ИИ-ассистент для бизнеса.

🎯 **Что я умею:**
• 📅 Управлять встречами и дедлайнами
• ✅ Следить за задачами
• 💰 Вести учёт финансов
• 🔔 Напоминать о важном
• 🧠 Помнить договорённости с контактами

💬 **Просто напишите мне:**
_"Встреча с Асхатом завтра в 14:00"_
_"Запиши доход 50000"_
_"Что у меня сегодня?"_

👇 **Или используйте кнопки:**"""


class TelegramBotService:
    """
    Service for managing Telegram bot interactions.
    Supports multiple bots (one per tenant) with interactive buttons.
    """
    
    def __init__(self) -> None:
        self._bots: Dict[UUID, Bot] = {}
        self._dispatchers: Dict[UUID, Dispatcher] = {}
    
    def get_bot(self, tenant_id: UUID, token: str) -> Bot:
        """Get or create a bot instance for a tenant."""
        if tenant_id not in self._bots:
            self._bots[tenant_id] = Bot(token=token)
        return self._bots[tenant_id]
    
    async def setup_webhook(self, tenant_id: UUID, token: str, base_url: str) -> str:
        """Set up webhook for a tenant's bot."""
        bot = self.get_bot(tenant_id, token)
        webhook_url = f"{base_url}/api/v1/webhooks/telegram/{tenant_id}"
        
        await bot.set_webhook(webhook_url)
        logger.info(f"Webhook set for tenant {tenant_id}: {webhook_url}")
        
        return webhook_url
    
    async def process_update(
        self, 
        tenant_id: UUID, 
        update_data: dict
    ) ->Optional[ dict ]:
        """Process an incoming Telegram update for a specific tenant."""
        async with async_session_maker() as db:
            tenant = await db.get(Tenant, tenant_id)
            if not tenant or not tenant.telegram_bot_token:
                logger.warning(f"Tenant {tenant_id} not found or no bot token")
                return None
            
            update = Update.model_validate(update_data)
            bot = self.get_bot(tenant_id, tenant.telegram_bot_token)
            lang = tenant.language or "ru"
            
            # Handle callback queries (button presses)
            if update.callback_query:
                return await self._handle_callback(
                    db, bot, update.callback_query, tenant, lang
                )
            
            # Handle messages
            message = update.message
            if not message:
                return None
            
            # Get or create user
            user = await self._get_or_create_user(
                db, tenant_id, 
                message.from_user.id,
                message.from_user.full_name
            )
            lang = user.language or tenant.language or "ru"
            
            # Get message text
            message_text = None
            if message.text:
                message_text = message.text
            elif message.voice:
                message_text = await self._transcribe_voice(
                    tenant.telegram_bot_token,
                    message.voice.file_id,
                    lang
                )
            
            if not message_text:
                return None
            
            # Handle commands
            if message_text.startswith("/"):
                await self._handle_command(bot, message, message_text, tenant, user, lang)
            else:
                chat_id = message.chat.id
                
                # Status Message
                status_msg = await bot.send_message(chat_id=chat_id, text="⏳ Обрабатываю...")
                
                async def update_status(msg: str):
                    try:
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=status_msg.message_id,
                            text=f"⏳ {msg}"
                        )
                    except Exception:
                        pass # Ignore if message not modified or error
                
                # UNIFIED: Use AIRouter instead of AgentRuntime
                # AIRouter is the same system used by Web and WhatsApp
                from app.services.ai_router import AIRouter
                router = AIRouter(db, language=lang)
                
                try:
                    response = await router.process_message(
                        tenant_id=tenant.id,
                        user_id=user.id,
                        message=message_text,
                        on_status=update_status
                    )
                    response_text = response.message if response.message else "Не удалось обработать запрос."
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Telegram AIRouter error: {e}")
                    response_text = f"❌ Ошибка: {str(e)}"
                
                # Cleanup status message
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
                except Exception:
                    pass

                # Try Markdown, fallback to plain text if parsing fails
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=response_text,
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    # Fallback to plain text
                    await bot.send_message(
                        chat_id=chat_id,
                        text=response_text
                    )
            return {"status": "ok"}
    
    async def _handle_callback(
        self,
        db: AsyncSession,
        bot: Bot,
        callback: CallbackQuery,
        tenant: Tenant,
        lang: str
    ) -> dict:
        """Handle button callback queries."""
        data = callback.data
        chat_id = callback.message.chat.id
        message_id = callback.message.message_id
        
        # Get user
        user = await self._get_or_create_user(
            db, tenant.id,
            callback.from_user.id,
            callback.from_user.full_name
        )
        lang = user.language or tenant.language or "ru"
        
        # Parse callback data
        action, value = data.split(":", 1) if ":" in data else (data, "")
        
        if action == "menu":
            await self._handle_menu_callback(bot, chat_id, message_id, value, lang)
        elif action == "action":
            await self._handle_action_callback(db, bot, chat_id, value, tenant, user, lang)
        elif action == "lang":
            await self._handle_language_change(db, bot, chat_id, message_id, user, value)
        elif action in ["meetings", "tasks", "finance", "birthdays", "ideas", "contracts"]:
            await self._handle_module_callback(db, bot, chat_id, action, value, tenant, user, lang)
        elif action == "contacts":
            await self._handle_contacts_callback(db, bot, chat_id, value, tenant, user, lang)
        elif action == "contact_action":
            await self._handle_contact_action(db, bot, chat_id, value, tenant, user, lang)
        elif action == "settings":
            await self._handle_settings_callback(db, bot, chat_id, message_id, value, user, lang)
        elif action in ["remind", "remind_time", "remind_before"]:
            await self._handle_reminder_callback(db, bot, chat_id, message_id, action, value, user, lang)
        
        # Answer callback to remove loading state
        try:
            await bot.answer_callback_query(callback.id)
        except:
            pass
        await db.commit()
        
        return {"status": "ok"}
    
    async def _handle_menu_callback(
        self,
        bot: Bot,
        chat_id: int,
        message_id: int,
        menu: str,
        lang: str
    ):
        """Handle menu navigation."""
        if menu == "main":
            keyboard = get_main_menu_keyboard(lang)
            text = "🏠 Главное меню" if lang == "ru" else "🏠 Басты мәзір"
        elif menu == "meetings":
            keyboard = get_meetings_keyboard(lang)
            text = "📅 Встречи" if lang == "ru" else "📅 Кездесулер"
        elif menu == "tasks":
            keyboard = get_tasks_keyboard(lang)
            text = "✅ Задачи" if lang == "ru" else "✅ Тапсырмалар"
        elif menu == "finance":
            keyboard = get_finance_keyboard(lang)
            text = "💰 Финансы" if lang == "ru" else "💰 Қаржы"
        elif menu == "contacts":
            keyboard = get_contacts_keyboard(lang)
            text = "📒 Контакты" if lang == "ru" else "📒 Байланыстар"
        elif menu == "birthdays":
            keyboard = get_birthdays_keyboard(lang)
            text = "🎂 Дни рождения" if lang == "ru" else "🎂 Туған күндер"
        elif menu == "ideas":
            keyboard = get_ideas_keyboard(lang)
            text = "💡 Идеи" if lang == "ru" else "💡 Идеялар"
        elif menu == "contracts":
            keyboard = get_contracts_keyboard(lang)
            text = "📄 Договоры" if lang == "ru" else "📄 Келісім-шарттар"
        elif menu == "settings":
            keyboard = get_settings_keyboard(lang)
            text = "⚙️ Настройки" if lang == "ru" else "⚙️ Баптаулар"
        elif menu == "help":
            keyboard = get_main_menu_keyboard(lang)
            text = self._get_help_text(lang)
        else:
            return
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    async def _handle_action_callback(
        self,
        db: AsyncSession,
        bot: Bot,
        chat_id: int,
        action: str,
        tenant: Tenant,
        user: User,
        lang: str
    ):
        """Handle action buttons."""
        if action == "briefing":
            # Generate morning briefing
            from app.services.morning_briefing import MorningBriefingService
            briefing_service = MorningBriefingService(
                db, api_key=tenant.gemini_api_key, language=lang
            )
            briefing = await briefing_service.generate_briefing(
                tenant.id, user.name or "Босс"
            )
            await bot.send_message(
                chat_id=chat_id,
                text=briefing,
                reply_markup=get_main_menu_keyboard(lang)
            )
    
    async def _handle_language_change(
        self,
        db: AsyncSession,
        bot: Bot,
        chat_id: int,
        message_id: int,
        user: User,
        new_lang: str
    ):
        """Change user language."""
        user.language = new_lang
        await db.flush()
        
        text = "✅ Язык изменён на русский" if new_lang == "ru" else "✅ Тіл қазақшаға өзгертілді"
        keyboard = get_main_menu_keyboard(new_lang)
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=keyboard
        )
    
    async def _handle_module_callback(
        self,
        db: AsyncSession,
        bot: Bot,
        chat_id: int,
        module: str,
        action: str,
        tenant: Tenant,
        user: User,
        lang: str
    ):
        """Handle module-specific callbacks."""
        text = ""
        keyboard = get_main_menu_keyboard(lang)
        
        if module == "meetings":
            from app.services.calendar_service import CalendarService
            from datetime import datetime, timedelta
            
            calendar = CalendarService(db)
            now = datetime.now()
            
            if action == "today":
                start = now.replace(hour=0, minute=0, second=0)
                end = start + timedelta(days=1)
                events = await calendar.get_events(tenant.id, start, end)
                
                if events:
                    if lang == "kz":
                        lines = ["📅 Бүгінгі кездесулер:"]
                    else:
                        lines = ["📅 Встречи сегодня:"]
                    for e in events[:5]:
                        time_str = datetime.fromisoformat(e["start_time"]).strftime("%H:%M")
                        lines.append(f"  {time_str} — {e['title']}")
                    text = "\n".join(lines)
                else:
                    text = "📅 Сегодня встреч нет" if lang == "ru" else "📅 Бүгін кездесу жоқ"

            elif action == "week":
                start = now.replace(hour=0, minute=0, second=0)
                end = start + timedelta(days=7)
                events = await calendar.get_events(tenant.id, start, end)
                
                if events:
                    if lang == "kz":
                        lines = ["📅 Осы аптадағы кездесулер:"]
                    else:
                        lines = ["📅 Встречи на этой неделе:"]
                    for e in events[:10]:
                        start_dt = datetime.fromisoformat(e["start_time"])
                        date_str = start_dt.strftime("%d.%m %H:%M")
                        lines.append(f"  {date_str} — {e['title']}")
                    text = "\n".join(lines)
                else:
                    text = "📅 На этой неделе встреч нет" if lang == "ru" else "📅 Осы аптада кездесу жоқ"
            
            elif action == "new":
                text = "💬 Напишите детали встречи:\n_Например: Встреча с Асхатом завтра в 14:00_" if lang == "ru" else "💬 Кездесу мәліметтерін жазыңыз:\n_Мысалы: Ертең Асхатпен кездесу 14:00_"
            
            keyboard = get_meetings_keyboard(lang)
        
        elif module == "tasks":
            from app.models.task import Task, TaskStatus
            
            if action == "overdue":
                stmt = select(Task).where(
                    Task.tenant_id == tenant.id,
                    Task.deadline < datetime.now(),
                    Task.status != TaskStatus.DONE.value
                ).limit(5)
                result = await db.execute(stmt)
                tasks = result.scalars().all()
                
                if tasks:
                    lines = ["🔥 Просроченные задачи:" if lang == "ru" else "🔥 Мерзімі өткен тапсырмалар:"]
                    for t in tasks:
                        lines.append(f"  • {t.title}")
                    text = "\n".join(lines)
                else:
                    text = "✅ Просроченных нет!" if lang == "ru" else "✅ Мерзімі өткен жоқ!"
            
            elif action == "all":
                stmt = select(Task).where(
                    Task.tenant_id == tenant.id,
                    Task.status != TaskStatus.DONE.value
                ).order_by(Task.deadline).limit(10)
                result = await db.execute(stmt)
                tasks = result.scalars().all()
                
                if tasks:
                    lines = ["📋 Все задачи:" if lang == "ru" else "📋 Барлық тапсырмалар:"]
                    for t in tasks:
                        deadline_str = t.deadline.strftime("%d.%m") if t.deadline else ""
                        lines.append(f"  • {t.title} ({deadline_str})")
                    text = "\n".join(lines)
                else:
                     text = "✅ Задач нет!" if lang == "ru" else "✅ Тапсырма жоқ!"

            elif action == "new":
                text = "💬 Опишите задачу:\n_Например: Сдать отчёт до пятницы_" if lang == "ru" else "💬 Тапсырманы жазыңыз:\n_Мысалы: Жұмаға дейін есеп тапсыру_"
            
            keyboard = get_tasks_keyboard(lang)
        
        elif module == "finance":
            if action in ["income", "expense"]:
                if action == "income":
                    text = "💸 Напишите сумму дохода:\n_Например: Доход 150000 от Асхата_" if lang == "ru" else "💸 Кіріс сомасын жазыңыз:\n_Мысалы: Асхаттан 150000 кіріс_"
                else:
                    text = "💳 Напишите сумму расхода:\n_Например: Расход 5000 на такси_" if lang == "ru" else "💳 Шығыс сомасын жазыңыз:\n_Мысалы: Таксиге 5000 шығыс_"
            
            elif action == "balance":
                # Get balance summary
                from app.models.finance import FinanceRecord
                from sqlalchemy import func
                
                income_stmt = select(func.sum(FinanceRecord.amount)).where(
                    FinanceRecord.tenant_id == tenant.id,
                    FinanceRecord.type == "income"
                )
                expense_stmt = select(func.sum(FinanceRecord.amount)).where(
                    FinanceRecord.tenant_id == tenant.id,
                    FinanceRecord.type == "expense"
                )
                
                income_result = await db.execute(income_stmt)
                expense_result = await db.execute(expense_stmt)
                
                total_income = float(income_result.scalar_one_or_none() or 0)
                total_expense = float(expense_result.scalar_one_or_none() or 0)
                balance = total_income - total_expense
                
                emoji = "📈" if balance >= 0 else "📉"
                if lang == "kz":
                    text = f"""📊 **Баланс**

💰 Жалпы кіріс: {total_income:,.0f} ₸
💳 Жалпы шығыс: {total_expense:,.0f} ₸

{emoji} **Баланс: {balance:,.0f} ₸**"""
                else:
                    text = f"""📊 **Баланс**

💰 Всего доходов: {total_income:,.0f} ₸
💳 Всего расходов: {total_expense:,.0f} ₸

{emoji} **Баланс: {balance:,.0f} ₸**"""
            
            elif action == "report":
                # Monthly report
                from app.models.finance import FinanceRecord
                from sqlalchemy import func
                
                now = datetime.now()
                month_start = now.replace(day=1, hour=0, minute=0, second=0).date()
                
                # This month income
                income_stmt = select(func.sum(FinanceRecord.amount)).where(
                    FinanceRecord.tenant_id == tenant.id,
                    FinanceRecord.type == "income",
                    FinanceRecord.record_date >= month_start
                )
                expense_stmt = select(func.sum(FinanceRecord.amount)).where(
                    FinanceRecord.tenant_id == tenant.id,
                    FinanceRecord.type == "expense",
                    FinanceRecord.record_date >= month_start
                )
                
                income_result = await db.execute(income_stmt)
                expense_result = await db.execute(expense_stmt)
                
                month_income = float(income_result.scalar_one_or_none() or 0)
                month_expense = float(expense_result.scalar_one_or_none() or 0)
                month_balance = month_income - month_expense
                
                # Count transactions
                count_stmt = select(func.count(FinanceRecord.id)).where(
                    FinanceRecord.tenant_id == tenant.id,
                    FinanceRecord.record_date >= month_start
                )
                count_result = await db.execute(count_stmt)
                tx_count = count_result.scalar_one_or_none() or 0
                
                emoji = "📈" if month_balance >= 0 else "📉"
                month_name = now.strftime("%B %Y")
                
                if lang == "kz":
                    text = f"""📈 **Айлық есеп: {month_name}**

💰 Кіріс: {month_income:,.0f} ₸
💳 Шығыс: {month_expense:,.0f} ₸
📝 Операциялар: {tx_count}

{emoji} **Айлық нәтиже: {month_balance:,.0f} ₸**"""
                else:
                    text = f"""📈 **Отчёт за {month_name}**

💰 Доходы: {month_income:,.0f} ₸
💳 Расходы: {month_expense:,.0f} ₸
📝 Операций: {tx_count}

{emoji} **Итог месяца: {month_balance:,.0f} ₸**"""
            
            keyboard = get_finance_keyboard(lang)
        
        elif module == "birthdays":
            if action == "new":
                text = "🎂 Введите имя и дату рождения:\n_Например: У Асхата день рождения 5 мая_" if lang == "ru" else "🎂 Аты мен туған күнін енгізіңіз:\n_Мысалы: Асхаттың туған күні 5 мамыр_"
            elif action == "upcoming":
                # Logic to find upcoming birthdays would go here
                text = "🎉 Ближайшие дни рождения: \n(Скоро будет реализовано)" if lang == "ru" else "🎉 Жақында болатын туған күндер: \n(Жақында қосылады)"
            elif action == "all":
                from app.models.birthday import Birthday
                stmt = select(Birthday).where(Birthday.tenant_id == tenant.id)
                result = await db.execute(stmt)
                birthdays = result.scalars().all()
                if not birthdays:
                    text = "Список пуст." if lang == "ru" else "Тізім бос."
                else:
                    text = "📋 Дни рождения:\n" if lang == "ru" else "📋 Туған күндер:\n"
                    for b in birthdays:
                        date_str = b.date.strftime("%d.%m")
                        text += f"  • {b.name}: {date_str}\n"
            
            keyboard = get_birthdays_keyboard(lang)

        elif module == "ideas":
            if action == "new":
                text = "💡 Опишите вашу идею:\n_Например: Идея открыть кофейню_" if lang == "ru" else "💡 Идеяңызды сипаттаңыз:\n_Мысалы: Кофейня ашу идеясы_"
            elif action == "all":
                from app.models.idea import Idea
                stmt = select(Idea).where(Idea.tenant_id == tenant.id)
                result = await db.execute(stmt)
                ideas = result.scalars().all()
                if not ideas:
                    text = "Идей пока нет." if lang == "ru" else "Идеялар әлі жоқ."
                else:
                    text = "💡 Ваши идеи:\n" if lang == "ru" else "💡 Сіздің идеяларыңыз:\n"
                    for i in ideas:
                        text += f"  • {i.title}\n"
            
            keyboard = get_ideas_keyboard(lang)

        elif module == "contracts":
            if action == "new":
                text = "📄 Отправьте фото договора или опишите его." if lang == "ru" else "📄 Келісім-шарт суретін жіберіңіз немесе сипаттаңыз."
            elif action == "expiring":
                 text = "⏳ Истекающие договоры:\n(Скоро будет реализовано)" if lang == "ru" else "⏳ Мерзімі аяқталатын келісім-шарттар:\n(Жақында қосылады)"
            elif action == "all":
                # Assuming Contract model exists or accessing via module logic
                 text = "📋 Все договоры:\n(Скоро будет реализовано)" if lang == "ru" else "📋 Барлық келісім-шарттар:\n(Жақында қосылады)"
            
            keyboard = get_contracts_keyboard(lang)
        
        if text:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    
    async def _handle_contacts_callback(
        self,
        db: AsyncSession,
        bot: Bot,
        chat_id: int,
        action: str,
        tenant: Tenant,
        user: User,
        lang: str
    ):
        """Handle contacts submenu actions."""
        from app.models.contact import Contact
        
        text = ""
        keyboard = get_contacts_keyboard(lang)
        
        if action == "all":
            stmt = select(Contact).where(Contact.tenant_id == tenant.id).limit(10)
            result = await db.execute(stmt)
            contacts = result.scalars().all()
            
            if contacts:
                lines = ["📒 Контакты:" if lang == "ru" else "📒 Байланыстар:"]
                for c in contacts:
                    phone_str = f" ({c.phone})" if c.phone else ""
                    lines.append(f"  • {c.name}{phone_str}")
                text = "\n".join(lines)
            else:
                text = "📒 Контактов пока нет" if lang == "ru" else "📒 Байланыстар әлі жоқ"
        
        elif action == "search":
            text = "🔍 Напишите имя для поиска:" if lang == "ru" else "🔍 Іздеу үшін атын жазыңыз:"
        
        elif action == "new":
            text = "➕ Напишите данные контакта:\n_Например: Асхат +77001234567_" if lang == "ru" else "➕ Байланыс деректерін жазыңыз:\n_Мысалы: Асхат +77001234567_"
        
        elif action == "frequent":
            # Contacts with most meetings
            stmt = select(Contact).where(Contact.tenant_id == tenant.id).limit(5)
            result = await db.execute(stmt)
            contacts = result.scalars().all()
            
            if contacts:
                lines = ["⭐ Частые контакты:" if lang == "ru" else "⭐ Жиі қолданылатын:"]
                for c in contacts[:5]:
                    lines.append(f"  • {c.name}")
                text = "\n".join(lines)
            else:
                text = "⭐ Пока нет частых контактов" if lang == "ru" else "⭐ Жиі қолданылатын әлі жоқ"
        
        if text:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    
    async def _handle_contact_action(
        self,
        db: AsyncSession,
        bot: Bot,
        chat_id: int,
        value: str,
        tenant: Tenant,
        user: User,
        lang: str
    ):
        """Handle individual contact actions (call, message, meet)."""
        from app.models.contact import Contact
        from uuid import UUID
        
        parts = value.split(":", 1)
        if len(parts) != 2:
            return
        
        action_type, contact_id = parts
        
        try:
            contact = await db.get(Contact, UUID(contact_id))
        except:
            contact = None
        
        if not contact:
            text = "❌ Контакт не найден" if lang == "ru" else "❌ Байланыс табылмады"
            await bot.send_message(chat_id=chat_id, text=text)
            return
        
        if action_type == "call":
            if contact.phone:
                text = f"📞 Позвоните: {contact.phone}" if lang == "ru" else f"📞 Қоңырау шалыңыз: {contact.phone}"
            else:
                text = "❌ Нет номера телефона" if lang == "ru" else "❌ Телефон нөмірі жоқ"
        
        elif action_type == "msg":
            text = f"💬 Напишите сообщение для {contact.name}:" if lang == "ru" else f"💬 {contact.name} үшін хабарлама жазыңыз:"
        
        elif action_type == "meet":
            text = f"📅 Напишите детали встречи с {contact.name}:" if lang == "ru" else f"📅 {contact.name} кездесу мәліметтерін жазыңыз:"
        
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    
    async def _handle_settings_callback(
        self,
        db: AsyncSession,
        bot: Bot,
        chat_id: int,
        message_id: int,
        action: str,
        user: User,
        lang: str
    ):
        """Handle settings submenu actions."""
        if action == "reminders":
            keyboard = get_reminders_keyboard(lang)
            text = "🔔 Настройки напоминаний" if lang == "ru" else "🔔 Еске салу баптаулары"
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard
            )
    
    async def _handle_reminder_callback(
        self,
        db: AsyncSession,
        bot: Bot,
        chat_id: int,
        message_id: int,
        action_type: str,
        value: str,
        user: User,
        lang: str
    ):
        """Handle reminder settings."""
        text = ""
        keyboard = get_reminders_keyboard(lang)
        
        if action_type == "remind_time":
            # Set morning briefing time
            hour = int(value)
            text = f"✅ Утренний брифинг установлен на {hour}:00" if lang == "ru" else f"✅ Таңғы брифинг {hour}:00-ге орнатылды"
            # TODO: Save to user preferences
        
        elif action_type == "remind_before":
            # Set meeting reminder time
            minutes = int(value)
            if minutes >= 60:
                time_str = f"{minutes // 60} час" if lang == "ru" else f"{minutes // 60} сағат"
            else:
                time_str = f"{minutes} мин"
            text = f"✅ Напоминание о встрече: за {time_str}" if lang == "ru" else f"✅ Кездесу еске салуы: {time_str} бұрын"
            # TODO: Save to user preferences
        
        elif action_type == "remind":
            if value == "morning":
                text = "🌅 Выберите время брифинга:" if lang == "ru" else "🌅 Брифинг уақытын таңдаңыз:"
            elif value == "meeting":
                text = "📅 За сколько напоминать о встрече:" if lang == "ru" else "📅 Кездесу туралы қашан еске салу:"
            elif value == "deadline":
                text = "✅ Напоминание о дедлайнах включено" if lang == "ru" else "✅ Дедлайн еске салуы қосылды"
        
        if text:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard
            )
    
    async def _handle_command(
        self,
        bot: Bot,
        message: Message,
        command: str,
        tenant: Tenant,
        user: User,
        lang: str
    ):
        """Handle bot commands with rich responses."""
        chat_id = message.chat.id
        
        if command.startswith("/start"):
            # Welcome message with buttons
            welcome = get_welcome_message(user.name or "друг", lang)
            keyboard = get_main_menu_keyboard(lang)
            
            await bot.send_message(
                chat_id=chat_id,
                text=welcome,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        elif command.startswith("/menu"):
            keyboard = get_main_menu_keyboard(lang)
            text = "🏠 Главное меню" if lang == "ru" else "🏠 Басты мәзір"
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
        
        elif command.startswith("/help"):
            text = self._get_help_text(lang)
            keyboard = get_main_menu_keyboard(lang)
            await bot.send_message(
                chat_id=chat_id, text=text, 
                reply_markup=keyboard, parse_mode="Markdown"
            )
        
        elif command.startswith("/briefing"):
            from app.services.morning_briefing import MorningBriefingService
            async with async_session_maker() as db:
                briefing_service = MorningBriefingService(
                    db, api_key=tenant.gemini_api_key, language=lang
                )
                briefing = await briefing_service.generate_briefing(tenant.id, user.name)
            await bot.send_message(chat_id=chat_id, text=briefing)
        
        elif command.startswith("/lang"):
            keyboard = get_settings_keyboard(lang)
            text = "🌐 Выберите язык:" if lang == "ru" else "🌐 Тіл таңдаңыз:"
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
        
        else:
            text = "❓ Неизвестная команда. Напишите /help" if lang == "ru" else "❓ Белгісіз команда. /help жазыңыз"
            await bot.send_message(chat_id=chat_id, text=text)
    
    def _get_help_text(self, lang: str) -> str:
        """Get help text."""
        if lang == "kz":
            return """❓ **Көмек**

**Командалар:**
/start — Бастау
/menu — Басты мәзір
/briefing — Бүгінгі брифинг
/lang — Тіл өзгерту
/help — Көмек

**Жазу мысалдары:**
• _"Ертең Асхатпен кездесу"_
• _"50 мың кіріс жаз"_
• _"Жұмаға дейін есеп тапсыру"_
• _"Бүгінге не жоспарланған?"_

Кез келген сұрақты жазыңыз! 🤖"""
        else:
            return """❓ **Помощь**

**Команды:**
/start — Начало
/menu — Главное меню
/briefing — Брифинг дня
/lang — Сменить язык
/help — Помощь

**Примеры сообщений:**
• _"Встреча с Асхатом завтра в 14:00"_
• _"Запиши доход 50000"_
• _"Сдать отчёт до пятницы"_
• _"Что у меня сегодня?"_

Просто напишите что угодно! 🤖"""
    
    async def _transcribe_voice(
        self,
        bot_token: str,
        file_id: str,
        language: str
    ) ->Optional[ str ]:
        """Transcribe a voice message."""
        try:
            from app.services.voice_transcriber import get_transcriber
            transcriber = get_transcriber()
            return await transcriber.transcribe_telegram_voice(bot_token, file_id, language)
        except Exception as e:
            logger.error(f"Voice transcription failed: {e}")
            return None
    
    async def _get_or_create_user(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        telegram_id: int,
        name: str
    ) -> User:
        """Get or create a user by Telegram ID."""
        stmt = select(User).where(
            User.tenant_id == tenant_id,
            User.telegram_id == telegram_id
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                tenant_id=tenant_id,
                telegram_id=telegram_id,
                name=name,
                role="user"
            )
            db.add(user)
            await db.flush()
        
        return user
    
    async def _process_message(
        self,
        db: AsyncSession,
        message: str,
        tenant: Tenant,
        user: User
    ) -> str:
        """Process a text message through AI Router."""
        lang = user.language or tenant.language or "ru"
        api_key = tenant.gemini_api_key or settings.gemini_api_key
        
        if not api_key:
            logger.warning(f"No Gemini API key for tenant {tenant.id}")
            return t("bot.error", lang)
        
        router = AIRouter(db, api_key=api_key, language=lang)
        response = await router.process_message(
            message=message,
            tenant_id=tenant.id,
            user_id=user.id
        )
        
        return response.message


# Global service instance
telegram_service = TelegramBotService()


def get_telegram_service() -> TelegramBotService:
    """Get the global Telegram service."""
    return telegram_service
