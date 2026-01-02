from __future__ import annotations
import json
from typing import List, Dict, Any, Optional
try:
    from ddgs import DDGS  # New package name
except ImportError:
    from duckduckgo_search import DDGS  # Fallback to old package
import httpx
from app.core.config import settings

class AssistantTools:
    """Tools available for the Assistant AI."""
    
    @staticmethod
    def search_web(query: str, max_results: int = 5) -> str:
        """
        Search the web for information using DuckDuckGo.
        Use this to find prices, news, facts, business contacts, or locations.
        """
        try:
            results = DDGS().text(query, max_results=max_results)
            if not results:
                return "Поиск не дал результатов."
            
            # Format results concisely
            formatted = []
            for r in results:
                title = r.get('title', 'No title')
                snippet = r.get('body', 'No content')
                href = r.get('href', '')
                formatted.append(f"Title: {title}\nLink: {href}\nContent: {snippet}\n---")
            
            return "\n".join(formatted)
        except Exception as e:
            return f"Ошибка поиска: {str(e)}"

    @staticmethod
    async def check_whatsapp(phone: str, instance_id: str, token: str) -> str:
        """
        Check if a phone number exists on WhatsApp.
        Phone should be digits only (e.g. 77011234567).
        """
        try:
            url = f"https://api.green-api.com/waInstance{instance_id}/checkWhatsapp/{token}"
            payload = {"phoneNumber": phone}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10)
                
            if response.status_code == 200:
                data = response.json()
                if data.get("existsWhatsapp"):
                    return f"Номер {phone} зарегистрирован в WhatsApp. ID: {data.get('wid')}"
                else:
                    return f"Номер {phone} НЕ зарегистрирован в WhatsApp."
            else:
                return f"Ошибка API: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Ошибка проверки номера: {str(e)}"

    @staticmethod
    async def send_whatsapp(phone: str, message: str, instance_id: str, token: str) -> str:
        """
        Send a WhatsApp message to a specific number.
        Use this to contact businesses or people.
        """
        try:
            # Format phone to chatId if needed (simple assumption)
            chat_id = f"{phone}@c.us" if "@" not in phone else phone
            
            url = f"https://api.green-api.com/waInstance{instance_id}/sendMessage/{token}"
            payload = {
                "chatId": chat_id,
                "message": message
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10)
                
            if response.status_code == 200:
                return f"Сообщение успешно отправлено на {phone}."
            else:
                return f"Ошибка отправки: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Ошибка отправки сообщения: {str(e)}"
