from __future__ import annotations
import json
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings

class AssistantTools:
    """Tools available for the Assistant AI."""
    
    @staticmethod
    async def search_web(query: str) -> str:
        """
        Search the web using Perplexity Online LLM.
        """
        if not settings.perplexity_api_key:
             return "❌ API Key для Perplexity не найден. Проверьте настройки (PERPLEXITY_API_KEY)."

        url = "https://api.perplexity.ai/chat/completions"
        payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            "messages": [
                {"role": "system", "content": "You are a helpful search engine. Be precise and provide up-to-date information. Include phone numbers and contacts if asked."},
                {"role": "user", "content": query}
            ]
        }
        headers = {
            "Authorization": f"Bearer {settings.perplexity_api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                
            if resp.status_code != 200:
                return f"Ошибка Perplexity API: {resp.status_code} - {resp.text}"
            
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            
            # Format as an observation
            return f"Результат поиска (Perplexity):\n{content}"
            
        except Exception as e:
            return f"Ошибка выполнения запроса к Perplexity: {str(e)}"


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

