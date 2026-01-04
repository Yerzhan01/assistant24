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


