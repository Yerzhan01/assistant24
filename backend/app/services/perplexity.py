from __future__ import annotations
import aiohttp
import json
import logging
from typing import Optional, List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class PerplexityClient:
    """
    Client for Perplexity AI API.
    Used for deep research, current events, and shopping/travel analysis.
    """
    
    BASE_URL = "https://api.perplexity.ai/chat/completions"
    MODEL = "sonar-pro"  # Best for research
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.perplexity_api_key
        
    async def search(self, query: str, system_prompt: str = "") -> str:
        """
        Perform a deep search using Perplexity.
        """
        if not self.api_key:
            return "❌ Ошибка: API ключ Perplexity не найден."
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Default system prompt for search
        if not system_prompt:
            system_prompt = "You are a helpful research assistant. Provide detailed, up-to-date information with citations if possible."
            
        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "temperature": 0.2,
            "max_tokens": 1000 # Enough for a summary
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.BASE_URL, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Perplexity API Error: {response.status} - {error_text}")
                        return f"❌ Ошибка поиска (API Error: {response.status})"
                    
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Log citations if useful (Perplexity usually embeds them or provides 'citations' field)
                    # For now just return content
                    return content
                    
        except Exception as e:
            logger.error(f"Perplexity Request Failed: {e}")
            return f"❌ Ошибка соединения: {e}"
