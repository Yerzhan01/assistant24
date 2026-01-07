from __future__ import annotations
from typing import List, Optional
from app.agents.base import BaseAgent, AgentTool
from app.services.whatsapp_bot import WhatsAppBotService
from app.services.perplexity import PerplexityClient
from app.models.tenant import Tenant
import logging

logger = logging.getLogger(__name__)

class TravelAgent(BaseAgent):
    """Travel Agent with Real-World Capabilities (Perplexity Search + WhatsApp)."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.whatsapp_service = WhatsAppBotService()
        self.search_client = PerplexityClient()

    @property
    def name(self) -> str:
        return "TravelAgent"

    @property
    def role_description(self) -> str:
        return "You are the Travel Specialist. You help plan trips, find hotels/flights using Deep AI Search (Perplexity), and can contact hotels via WhatsApp."

    def get_system_prompt(self) -> str:
        return f"""
        Ты — Продвинутый Travel-агент цифрового секретаря.
        
        ТВОИ ВОЗМОЖНОСТИ:
        1. 🧠 **Глубокий Поиск (Perplexity AI)**:
           - Используй `search_hotels` и `search_flights`.
           - Perplexity сам проанализирует множество сайтов и выдаст готовое резюме с ценами и контактами.
           - Тебе не нужно гадать — просто передай запрос и покажи ответ пользователю.
        
        2. 📱 **Контакт с отелем (WhatsApp)**:
           - Если нашел номер телефона отеля, можешь написать им через `contact_hotel`.
           - Спрашивай наличие мест, цены или бронируй.
           - Если пользователь просит "забронируй" или "узнай детали" — сразу пиши в отель.
        
        ИНСТРУКЦИИ:
        - Если пользователь ищет отель -> `search_hotels` (запрос улетит в Perplexity).
        - Если пользователь хочет авиабилеты -> `search_flights`.
        - Если нужно узнать наличие мест у конкретного отеля -> `contact_hotel`.
        
        Язык: {self.language}
        """

    def get_tools(self) -> List[AgentTool]:
        return [
            AgentTool(
                name="search_hotels",
                description="Поиск отелей и сравнение цен через Perplexity AI. Находит цены, отзывы и телефоны.",
                parameters={
                    "city": {"type": "string", "description": "Город"},
                    "query": {"type": "string", "description": "Детали (бюджет, даты, пожелания)"}
                },
                function=self._search_hotels
            ),
            AgentTool(
                name="search_flights",
                description="Поиск авиабилетов через Perplexity AI.",
                parameters={
                    "from_city": {"type": "string", "description": "Откуда"},
                    "to_city": {"type": "string", "description": "Куда"},
                    "date": {"type": "string", "description": "Дата"}
                },
                function=self._search_flights
            ),
            AgentTool(
                name="contact_hotel",
                description="Написать сообщение в отель через WhatsApp (нужен номер телефона).",
                parameters={
                    "hotel_name": {"type": "string", "description": "Название отеля"},
                    "phone": {"type": "string", "description": "Номер телефона (с кодом страны)"},
                    "message": {"type": "string", "description": "Текст сообщения"}
                },
                function=self._contact_hotel
            ),
            AgentTool(
                name="get_city_info",
                description="Информация о городе (виза, валюта, погода) через Perplexity.",
                parameters={
                    "city": {"type": "string", "description": "Город"}
                },
                function=self._get_city_info
            )
        ]
    
    async def _search_hotels(self, city: str = "", query: str = "", location: str = "", **kwargs) -> str:
        """Search hotels using Perplexity."""
        target_city = city or location
        if not target_city:
            return "❌ Укажите город (city) для поиска отеля."

        # Handle extra arguments from model hallucinations
        extra_info = ", ".join([f"{k}: {v}" for k, v in kwargs.items()])
        full_query = query
        if extra_info:
            full_query += f" ({extra_info})"

        user_query = f"Find hotels in {target_city} meeting these criteria: {full_query}. Include prices in local currency and USD, average rating. IMPORTANT: You MUST find the phone number (WhatsApp or Reception) for each hotel. Search their official Facebook/Instagram/Website pages if needed."
        
        logger.info(f"🔎 Perplexity Search: {user_query}")
        result = await self.search_client.search(
            query=user_query,
            system_prompt="You are a travel assistant. Search for hotels. ANSWER STRICTLY IN RUSSIAN LANGUAGE (Русский язык). List 3-5 best hotel options. For each, strictly provide: Name, Stars, Approx Price/Night, Pros/Cons, and CONTACT PHONE (Required). If specific WhatsApp not found, provide the main reception number. Format cleanly with emojis."
        )
        
        return f"""🏨 **Анализ отелей в {city} (Perplexity):**
        
{result}

💡 **Чтобы сохранить отель в контакты:**
Скажите, например: "Сохрани первый вариант" или "Запиши контакт отеля Роза".
(Я не сохраняю контакты автоматически, чтобы не создавать мусор)."""

    async def _search_flights(self, from_city: str, to_city: str, date: str = "") -> str:
        """Search flights using Perplexity."""
        user_query = f"Find flights from {from_city} to {to_city} for date {date}. Compare prices, duration, and stopovers."
        
        logger.info(f"🔎 Perplexity Flight Search: {user_query}")
        result = await self.search_client.search(
            query=user_query,
            system_prompt="You are a flight expert. Find current flight options. List airlines, prices, duration. Suggest the best value option."
        )
        
        return f"""✈️ **Анализ рейсов {from_city} -> {to_city}:**
        
{result}

🔗 Бронировать лучше через aviasales.kz или официальные сайты."""

    async def _contact_hotel(self, hotel_name: str, phone: str, message: str) -> str:
        """Send WhatsApp message to hotel."""
        # 1. Validate info
        if not phone or len(phone) < 10:
            return "❌ Некорректный номер телефона."
        
        # 2. Get Tenant Credentials
        tenant = await self.db.get(Tenant, self.tenant_id)
        if not tenant or not tenant.greenapi_instance_id:
            return "❌ Ошибка: WhatsApp не настроен для этого аккаунта (нужен Green API)."
            
        # 3. Send Message
        try:
            # Format phone
            clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
            
            # Send (No footer as requested)
            full_msg = message
            
            await self.whatsapp_service.send_message(
                tenant.greenapi_instance_id,
                tenant.greenapi_token,
                clean_phone,
                full_msg
            )
            
            return f"✅ **Отправлено:** Сообщение в **{hotel_name}** ({clean_phone}) успешно ушло!\n📝 Текст: \"{message}\""
            
        except Exception as e:
            logger.error(f"Failed to contact hotel: {e}")
            return f"❌ Ошибка отправки: {str(e)}"

    async def _get_city_info(self, city: str) -> str:
        """Get city info via Perplexity."""
        return await self.search_client.search(
            query=f"Travel guide for {city}. Need info on: Visa requirements for Kazakhstan citizens, Currency exchange, Weather now, Top 3 Must-see sights.",
            system_prompt="Provide a concise travel guide."
        )
