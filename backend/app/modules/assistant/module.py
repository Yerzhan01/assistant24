from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Optional
from uuid import UUID
import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.i18n import t
from app.models.tenant import Tenant
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse
from app.modules.assistant.tools import AssistantTools

class AssistantModule(BaseModule):
    """
    Assistant module that uses tools (Search, WhatsApp) to solve complex tasks.
    """
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        # Configure local Gemini instance for the agent loop
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel(settings.gemini_model)
        else:
            self.model = None
    
    @property
    def info(self) -> ModuleInfo:
        return ModuleInfo(
            module_id="assistant",
            name_ru="Ассистент",
            name_kz="Көмекші",
            description_ru="Поиск в интернете и выполнение поручений",
            description_kz="Интернеттен іздеу және тапсырмаларды орындау",
            icon="🌐"
        )
    
    async def process(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID, 
        user_id: Optional[UUID] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Run the ReAct agent loop to solve the user's request."""
        if not self.model:
            return ModuleResponse(success=False, message="API Key not configured for Assistant.")
            
        user_query = intent_data.get("query") or intent_data.get("original_message")
        if not user_query:
            return ModuleResponse(success=False, message="Пустой запрос.")

        # Get tenant for WhatsApp credentials
        tenant = await self.db.get(Tenant, tenant_id)
        wa_instance = tenant.greenapi_instance_id if tenant else None
        wa_token = tenant.greenapi_token if tenant else None

        # Get context from router
        rag_context = intent_data.get("rag_context", "")

        # Prepare tools context
        tools_desc = """
1. search_web(query: str): Поиск информации в Google/DuckDuckGo. Используй для поиска цен, фактов, мест, контактов.
2. check_whatsapp(phone: str): Проверка наличия WhatsApp на номере. Номер должен быть чистым (без +, пробелов).
3. send_whatsapp(phone: str, message: str): Отправка сообщения в WhatsApp. Используй ТОЛЬКО если пользователь явно попросил написать.
"""
        
        system_prompt = f"""
Ты — умный ИИ-ассистент с доступом к инструментам. Твоя задача — выполнить просьбу пользователя.
Не выдумывай информацию. Если чего-то не знаешь — ищи в интернете.

Контекст разговора (память):
{rag_context}

ПРАВИЛО БЕЗОПАСНОСТИ (WhatsApp):
Перед использованием инструмента `send_whatsapp` ты ОБЯЗАН получить явное подтверждение от пользователя.
1. Если ты нашел контакт и хочешь написать: СНАЧАЛА выведи `Final Answer` с текстом "Я нашел номер <номер>. Написать им: '<текст>'?".
2. НЕ вызывай `send_whatsapp` в этом же шаге.
3. Только если пользователь ответил "Да", "Отправляй" (см. запрос или контекст) — тогда вызывай инструмент.

Инструменты:
{tools_desc}

Формат твоих размышлений (строго следуй ему):
Thought: <твои мысли, что делать дальше>
Tool: <название_инструмента>
Args: <аргументы в формате JSON, например {{"query": "..."}}>

Я выполню инструмент и верну тебе результат в формате "Observation: ...".
Когда у тебя будет готов окончательный ответ для пользователя, верни его в формате:
Final Answer: <твой ответ>

Текущая дата: 2026-01-01
Запрос пользователя: {user_query}
"""

        history = [system_prompt]
        max_steps = 5
        
        for step in range(max_steps):
            # Generate next step
            try:
                # Full prompt so far
                full_prompt = "\n".join(history)
                response = self.model.generate_content(full_prompt)
                response_text = response.text.strip()
                history.append(f"Step {step+1}: {response_text}")
                
                # Parse response
                if "Final Answer:" in response_text:
                    final_answer = response_text.split("Final Answer:", 1)[1].strip()
                    return ModuleResponse(success=True, message=final_answer)
                
                # Detect tool call
                tool_match = re.search(r"Tool:\s*(\w+)", response_text)
                args_match = re.search(r"Args:\s*(\{.*?\})", response_text, re.DOTALL)
                
                if tool_match and args_match:
                    tool_name = tool_match.group(1)
                    try:
                        tool_args = json.loads(args_match.group(1))
                    except:
                        history.append("Observation: Ошибка парсинга аргументов (невалидный JSON).")
                        continue
                        
                    # Execute tool
                    observation = await self._execute_tool(tool_name, tool_args, wa_instance, wa_token)
                    history.append(f"Observation: {observation}")
                    
                else:
                    # If model just talks without tool or final answer, check if it's the answer
                    if not tool_match:
                         # Treat entire response as answer if it looks like one
                         return ModuleResponse(success=True, message=response_text)
                    
            except Exception as e:
                history.append(f"Observation: Internal Error: {str(e)}")
        
        return ModuleResponse(success=False, message="Не удалось выполнить задачу за отведенное число шагов.")

    async def _execute_tool(self, name: str, args: dict, instance_id: str, token: str) -> str:
        try:
            if name == "search_web":
                return AssistantTools.search_web(args.get("query", ""))
            elif name == "check_whatsapp":
                if not instance_id or not token:
                    return "Ошибка: WhatsApp не подключен в настройках."
                return await AssistantTools.check_whatsapp(args.get("phone"), instance_id, token)
            elif name == "send_whatsapp":
                if not instance_id or not token:
                    return "Ошибка: WhatsApp не подключен в настройках."
                return await AssistantTools.send_whatsapp(args.get("phone"), args.get("message"), instance_id, token)
            else:
                return f"Неизвестный инструмент: {name}"
        except Exception as e:
            return f"Ошибка выполнения инструмента {name}: {str(e)}"

    def get_ai_instructions(self, language: str = "ru") -> str:
        # This is for the Router to decide when to route requests to this module
        return """
Все запросы, требующие поиска в интернете, актуальной информации (погода, цены, новости) или активных действий (написать в WhatsApp, найти контакт).
Примеры: "Найди отель в Ташкенте", "Какая погода в Алматы?", "Найди номер СТО и напиши им".
"""

    def get_intent_keywords(self) -> List[str]:
        return ["найди", "поищи", "узнай", "search", "google", "интернет", "билеты", "отель", "погода"]
