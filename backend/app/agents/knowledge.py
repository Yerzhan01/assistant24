from __future__ import annotations
from typing import List, Optional
from app.agents.base import BaseAgent, AgentTool, AgentResponse
from app.services.perplexity import PerplexityClient
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class KnowledgeAgent(BaseAgent):
    """
    Knowledge Agent with Perplexity AI capabilities.
    Uses 'sonar-pro' for deep research and analysis.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_client = PerplexityClient()
    
    @property
    def name(self) -> str:
        return "KnowledgeAgent"

    @property
    def role_description(self) -> str:
        return "You are the Knowledge Specialist. You perform deep research using Perplexity AI."

    def get_system_prompt(self) -> str:
        return f"""
        Ты — Агент Знаний цифрового секретаря.
        Твой мозг — Perplexity AI (модель sonar-pro).
        
        Твоя задача — давать ГЛУБОКИЕ, полные и проверенные ответы.
        Не просто "первая ссылка", а анализ нескольких источников.
        
        Если ищешь человека/компанию:
        1. Найди официальный сайт.
        2. Найди профили в соцсетях.
        3. Найди контактные данные (телефоны, email).
        4. Сделай краткое саммари "Кто это и чем занимается".
        
        Язык: {self.language}
        """

    def get_tools(self) -> List[AgentTool]:
        # No custom tools, Perplexity handles the search logic internally via API
        return []
    
    async def run(self, message: str, context: Optional[str] = None) -> AgentResponse:
        """
        Use Perplexity AI for deep research.
        """
        try:
            # Build prompt for Perplexity
            system_instruction = self.get_system_prompt()
            
            # Run search
            logger.info(f"🔎 Perplexity Knowledge Search: {message}")
            result_text = await self.search_client.search(
                query=message,
                system_prompt=system_instruction
            )
            
            # Check for error prefix from client
            if result_text.startswith("❌"):
                 return AgentResponse(content=result_text)

            return AgentResponse(content=f"🧠 {result_text}")
            
        except Exception as e:
            logger.error(f"KnowledgeAgent Perplexity error: {e}")
            return AgentResponse(content=f"❌ Ошибка поиска: {e}")

