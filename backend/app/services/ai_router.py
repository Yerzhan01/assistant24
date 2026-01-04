from __future__ import annotations
"""AI Router - Intent classification and data extraction using Google Gemini with RAG."""
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import UUID

import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.i18n import t
from app.modules.base import BaseModule, ModuleResponse
from app.modules.registry import get_registry
from app.services.tracing import TracingService, TraceContext

logger = logging.getLogger("ai_router")


class AIRouter:
    """
    AI Router uses Google Gemini to:
    1. Retrieve relevant context from memory (RAG)
    2. Classify user intent (which module to use)
    3. Extract structured data for the module
    4. Store conversation as memory
    """
    
    def __init__(
        self, 
        db: AsyncSession,
        api_key: Optional[str] = None,
        language: str = "ru",
        enable_rag: bool = True,
        thinking_level: str = None
    ) -> None:
        self.db = db
        self.language = language
        self.enable_rag = enable_rag
        self.thinking_level = thinking_level or settings.gemini_thinking_level
        
        # Configure Gemini
        key = api_key or settings.gemini_api_key
        if key:
            genai.configure(api_key=key)
            # Configure generation with thinking level for Gemini 3
            generation_config = {
                "temperature": 1.0,  # Recommended for Gemini 3
            }
            self.model = genai.GenerativeModel(
                settings.gemini_model,
                generation_config=generation_config
            )
        else:
            self.model = None
    
    def _build_system_prompt(
        self, 
        modules: List[BaseModule],
        context: str = "",
        message_history: List[Dict[str, str]] = None
    ) -> str:
        """Build system prompt with instructions from all enabled modules and RAG context."""
        registry = get_registry()
        module_instructions = registry.build_ai_prompt(modules, self.language)
        
        # Format history
        history_str = ""
        if message_history:
            history_lines = []
            for msg in message_history[-5:]: # Last 5 messages
                role = "User" if msg["role"] == "user" else "Assistant"
                history_lines.append(f"{role}: {msg['content']}")
            history_str = "\n".join(history_lines)
        
        if self.language == "kz":
            base_prompt = """
Сіз — ақылды цифрлық хатшысыз. Пайдаланушының сұрауын талдап, БІРНЕШЕ ниетін (intents) анықтаңыз.

⛔ МАҢЫЗДЫ ШЕКТЕУЛЕР:
- Сіз бизнес-ассистентсіз, интернетке қосылмағансыз.
- Тек пайдаланушы берген немесе жадта (RAG) бар деректермен жұмыс істейсіз.
- Валюта бағамдары, ауа райы, жаңалықтар туралы сұраққа: "Менде интернетке қол жетімділік жоқ, мен тек сіздің істеріңізді басқарамын" деп жауап беріңіз.
- Медициналық, заңгерлік немесе инвестициялық кеңес БЕРМЕҢІЗ.

МАҢЫЗДЫ: Пайдаланушы бір хабарламада бірнеше тапсырма бере алады. БАРЛЫҒЫН тізімге қосыңыз.

Ниет түрлері:
{module_list}
- "schedule_meeting" — кездесу ұйымдастыру
- "recall" — өткен ақпаратты еске түсіру

Алдыңғы диалог:
{history_str}

{context_block}

Қайтару форматы (тек JSON):
{{
  "reasoning": "<сіздің логикаңызды түсіндіріңіз>",
  "intents": [
    {{
      "intent": "<module_id>",
      "confidence": <0.0-1.0>,
      "data": {{ ... }}
    }}
  ]
}}

Егер БІРНЕШЕ ниет болса, барлығын intents массивіне қосыңыз.
Мысалы: "Асхатқа 50к төледім, ертең кездесу" -> finance + meeting.

Егер ниетті анықтай алмасаңыз:
{{
  "reasoning": "Тапсырма табылмады",
  "intents": [{{"intent": "unknown", "confidence": 0.0, "data": {{}}}}]
}}

Пайдаланушының жергілікті уақыты: {current_datetime}

Модульдер нұсқаулары:

{module_instructions}
"""
        else:
            base_prompt = """
Ты — умный цифровой секретарь. Проанализируй запрос пользователя и определи ВСЕ намерения (intents).

⛔ КРИТИЧЕСКИЕ ОГРАНИЧЕНИЯ:
- Ты бизнес-ассистент, у тебя НЕТ доступа к интернету.
- Ты работаешь ТОЛЬКО с данными пользователя или из памяти (RAG).
- На вопросы о курсах валют, погоде, новостях, ценах акций отвечай: "У меня нет доступа к интернету, я управляю только вашими делами."
- НЕ давай медицинских, юридических или инвестиционных советов.
- НЕ придумывай данные, которых нет в контексте.

ВАЖНО: Пользователь может дать несколько задач в одном сообщении. Выдели ВСЕ действия.

Возможные намерения:
{module_list}
- "schedule_meeting" — организовать встречу
- "recall" — вспомнить прошлую информацию

Предыдущий диалог:
{history_str}

{context_block}

Формат ответа (только JSON):
{{
  "reasoning": "<объясни свою логику: почему ты выделил эти намерения>",
  "intents": [
    {{
      "intent": "<module_id>",
      "confidence": <0.0-1.0>,
      "data": {{ ... }}
    }}
  ]
}}

Если в сообщении НЕСКОЛЬКО действий, добавь ВСЕ в массив intents.
Пример: "Заплатил Асхату 50к за встречу завтра" -> finance + meeting.

Если не можешь определить намерение:
{{
  "reasoning": "Не удалось определить задачу",
  "intents": [{{"intent": "unknown", "confidence": 0.0, "data": {{}}}}]
}}

Локальное время пользователя: {current_datetime}

Инструкции по модулям:

{module_instructions}
"""
        
        module_list = ", ".join([m.module_id for m in modules])
        
        # Build context block for RAG
        if context:
            if self.language == "kz":
                context_block = f"Жадтан табылған ақпарат:\n{context}"
            else:
                context_block = f"Найденная информация из памяти:\n{context}"
        else:
            context_block = ""
        
        # Use Kazakhstan timezone (UTC+5) for user-facing datetime
        # TODO: In production, get timezone from Tenant settings
        from datetime import timezone, timedelta
        kz_tz = timezone(timedelta(hours=5))
        local_now = datetime.now(kz_tz)
        
        return base_prompt.format(
            module_list=module_list,
            current_datetime=local_now.strftime("%Y-%m-%d %H:%M (%A)"),
            module_instructions=module_instructions,
            context_block=context_block,
            history_str=history_str
        )
    
    async def get_rag_context(
        self,
        tenant_id: UUID,
        message: str
    ) -> str:
        """Retrieve relevant context from memory using semantic search."""
        if not self.enable_rag:
            return ""
        
        try:
            from app.services.embedding_service import EmbeddingService
            embedding_service = EmbeddingService(self.db)
            return await embedding_service.get_context_for_query(
                tenant_id=tenant_id,
                query=message,
                max_context_length=1500
            )
        except Exception as e:
            # RAG is optional, continue without context on error
            return ""
    
    async def classify_intent(
        self, 
        message: str, 
        modules: List[BaseModule],
        context: str = "",
        message_history: List[Dict[str, str]] = None,
        image_data: bytes = None
    ) -> Dict[str, Any]:
        """
        Classify user intent and extract data.
        Supports multimodal input (Text + Image).
        Returns dict with classification result + '_meta' key for usage stats.
        """
        if not self.model:
            # Fallback: keyword-based classification
            logger.warning("Gemini model not initialized, using fallback classification")
            return self._fallback_classify(message, modules)
        
        module_ids = [m.module_id for m in modules]
        logger.info(f"Classifying intent with modules: {module_ids} for message: {message[:50]}...")
        
        system_prompt = self._build_system_prompt(modules, context, message_history)
        
        # Prepare inputs
        inputs = [
            {"role": "user", "parts": [system_prompt]},
            {"role": "model", "parts": ["Понял. Жду сообщение пользователя."]}
        ]
        
        # If image provided, add it to user message
        user_parts = [message]
        if image_data:
            from app.core.config import settings
            import google.generativeai as genai
            
            # Additional Instruction for Vision
            user_parts[0] = f"""
            [IMAGE UPLOADED]
            Пользователь отправил фото.
            
            Твоя задача:
            1. Проанализируй изображение. Это чек, счет или документ?
            2. Извлеки СУММУ, ДАТУ и КАТЕГОРИЮ (если это расход).
            3. Если это чек -> Intent: 'expense' (finance).
            4. Если это просто картинка без текста -> ответь что видишь.
            
            Текст пользователя: {message}
            """
            
            try:
                # Create Image Part
                # Gemini expects dict: {'mime_type': 'image/jpeg', 'data': bytes}
                image_part = {
                    "mime_type": "image/jpeg", 
                    "data": image_data
                }
                user_parts.append(image_part)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to attach image to Gemini: {e}")
                
        inputs.append({"role": "user", "parts": user_parts})
        
        try:
            response = self.model.generate_content(inputs)
            
            text = response.text.strip()
            logger.info(f"Gemini Raw Response: {text}")
            
            # Clean up markdown code blocks if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            result = json.loads(text)

            # HARD OVERRIDE: Check if user wants to send WhatsApp message but AI failed
            try:
                msg_lower = message.lower().strip()
                wa_keywords = ["напиши", "отправь", "скажи", "жаз", "жібер", "write", "send"]
                
                # If message contains messaging keywords (not just starts with)
                is_messaging_request = any(kw in msg_lower for kw in wa_keywords)
                
                current_intents = result.get("intents", [])
                first_intent = current_intents[0].get("intent") if current_intents else "unknown"
                
                # Check if whatsapp module is enabled
                whatsapp_enabled = any(m.module_id == "whatsapp" for m in modules)

                if is_messaging_request and first_intent != "whatsapp" and whatsapp_enabled:
                    logger.warning(f"Overriding intent '{first_intent}' -> 'whatsapp' based on keywords")
                    result["intents"] = [{
                        "intent": "whatsapp",
                        "confidence": 1.0,
                        "data": {
                            "action": "send_message",
                            "content": message,
                            "original_message": message
                        }
                    }]
            except Exception as e:
                logger.error(f"Error in intent override logic: {e}")
            
            # Attach metadata
            if hasattr(response, "usage_metadata"):
                result["_meta"] = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "response_tokens": response.usage_metadata.candidates_token_count,
                    "model": settings.gemini_model
                }
            
            return result
            
        except Exception as e:
            # Fallback on error
            return self._fallback_classify(message, modules)
    
    def _fallback_classify(
        self, 
        message: str, 
        modules: List[BaseModule]
    ) -> Dict[str, Any]:
        """Keyword-based fallback classification."""
        message_lower = message.lower()
        
        # Check for meeting scheduling keywords (BUT exclude cancellation)
        schedule_keywords = ["организуй встречу", "запланируй", "договорись о встрече", 
                           "согласуй время", "кездесу ұйымдастыр"]
        
        cancel_keywords = ["удалить", "отменить", "убери", "жою", "болдырмау", "алып тастау"]
        if any(kw in message_lower for kw in cancel_keywords) and "встреч" in message_lower:
             return {
                "reasoning": "Обнаружен запрос на удаление встречи (ключевые слова)",
                "intents": [{"intent": "cancel_meeting", "confidence": 0.9, "data": {}}]
            }

        # Priority: WhatsApp Messaging
        wa_keywords = ["напиши", "отправь", "скажи", "жаз", "жібер", "write", "send"]
        if any(message_lower.startswith(kw) or f" {kw} " in f" {message_lower} " for kw in wa_keywords):
            # Check if whatsapp module is enabled
            if any(m.module_id == "whatsapp" for m in modules):
                # Extract potential name simply (naive)
                return {
                    "reasoning": "Обнаружен прямой запрос на отправку сообщения (Priority)",
                    "intents": [{"intent": "whatsapp", "confidence": 0.95, "data": {"action": "send_message", "original_message": message}}]
                }

        if any(kw in message_lower for kw in schedule_keywords):
            return {
                "reasoning": "Обнаружен запрос на организацию встречи",
                "intents": [{"intent": "schedule_meeting", "confidence": 0.8, "data": {"original_message": message}}]
            }
        
        # Check for recall keywords
        recall_keywords = ["напомни", "о чем договорились", "что было", "вспомни",
                          "еске түсір", "не келістік"]
        if any(kw in message_lower for kw in recall_keywords):
            return {
                "reasoning": "Обнаружен запрос на воспоминание информации",
                "intents": [{"intent": "recall", "confidence": 0.7, "data": {"query": message}}]
            }
        
        # Collect ALL matching intents (multi-intent support in fallback)
        matched_intents = []
        
        for module in modules:
            keywords = module.get_intent_keywords()
            score = sum(1 for kw in keywords if kw.lower() in message_lower)
            
            if score >= 1:
                matched_intents.append({
                    "intent": module.module_id,
                    "confidence": min(0.3 + (score * 0.1), 0.7),
                    "data": {}
                })
        
        if matched_intents:
            return {
                "reasoning": f"Найдено по ключевым словам: {', '.join([i['intent'] for i in matched_intents])}",
                "intents": matched_intents
            }
        
        return {
            "reasoning": "Не удалось определить намерение",
            "intents": [{"intent": "unknown", "confidence": 0.0, "data": {}}]
        }
    
    async def process_message(
        self,
        message: str,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        enabled_modules: Optional[List[BaseModule]] = None,
        source: str = "web",
        silent_response: bool = False,
        image_data: bytes = None,
        on_status: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> ModuleResponse:
        """
        Process a user message end-to-end:
        1. Retrieve RAG context
        2. Classify intent
        3. Route to appropriate module or negotiator
        4. Store conversation as memory
        5. Return response
        
        Args:
            silent_response: If True, executes actions but does not save bot response to history or return text.
            image_data: Optional image bytes for multimodal analysis (Vision).
        
        All steps are traced for debugging.
        """
        # Initialize tracing
        tracing = TracingService(self.db)
        trace = tracing.start_trace(
            tenant_id=tenant_id,
            user_message=message,
            user_id=user_id,
            source=source
        )
        
        try:
            # Use Agent Runtime for unified execution (Web & Telegram)
            from app.agents.runtime import AgentRuntime
            from app.models.chat import Message
            from sqlalchemy import select, desc
            
            # Get message history (last 10 messages)
            history_stmt = select(Message).where(
                Message.tenant_id == tenant_id
            ).order_by(desc(Message.created_at)).limit(10)
            
            result = await self.db.execute(history_stmt)
            db_messages = result.scalars().all()
            
            # Convert to format for runtime
            history = [{"role": "user" if m.is_user else "assistant", "content": m.content} for m in reversed(db_messages)]
            
            # Initialize Runtime
            runtime = AgentRuntime(self.db, tenant_id, user_id, self.language)
            
            # Save User Message
            if not silent_response:
                user_msg = Message(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    is_user=True,
                    content=message,
                    intent="web_message"
                )
                self.db.add(user_msg)
                await self.db.commit() # Commit so Runtime can see it if needed
            
            # Execute
            response_text = await runtime.run(message, history=history, on_status=on_status)
            
            # Save Assistant Response
            if not silent_response:
                bot_msg = Message(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    is_user=False,
                    content=response_text,
                    intent="runtime_response"
                )
                self.db.add(bot_msg)
                await self.db.commit()
            
            trace.set_final_response(response_text, success=True)
            return ModuleResponse(success=True, message=response_text)
            
        except Exception as e:
            trace.log_error(type(e).__name__, str(e))
            return ModuleResponse(
                success=False,
                message=f"Произошла ошибка: {str(e)}"
            )
        finally:
            await trace.save()
    
    async def _process_message_with_trace(
        self,
        message: str,
        tenant_id: UUID,
        user_id: Optional[UUID],
        enabled_modules: Optional[List[BaseModule]],
        trace: TraceContext,
        silent_response: bool = False,
        image_data: bytes = None
    ) -> ModuleResponse:
        """Internal method that processes message with tracing."""
        # Get enabled modules
        trace.start_step("get_modules")
        if enabled_modules is None:
            registry = get_registry()
            enabled_modules = await registry.get_enabled_modules(self.db, tenant_id)
        
        trace.end_step("get_modules", {"count": len(enabled_modules) if enabled_modules else 0})
        
        if not enabled_modules:
            trace.log_error("NoModules", "No enabled modules found")
            return ModuleResponse(
                success=False,
                message=t("bot.error", self.language)
            )
        
        # Get message history (last 5 messages)
        message_history = []
        try:
            from sqlalchemy import select, desc
            from app.models.chat import Message
            
            stmt = select(Message).where(
                Message.tenant_id == tenant_id
            ).order_by(desc(Message.created_at)).limit(5)
            
            result = await self.db.execute(stmt)
            messages = result.scalars().all()
            
            # Convert to format for prompt (reverse order to be chronological)
            for msg in reversed(messages):
                message_history.append({
                    "role": "user" if msg.is_user else "assistant",
                    "content": msg.content
                })
        except Exception as e:
            trace.log_step("get_history", error=str(e))
        
        # Get RAG context
        trace.start_step("rag_retrieval")
        context = await self.get_rag_context(tenant_id, message)
        trace.end_step("rag_retrieval", {"context_length": len(context) if context else 0})
        trace.log_rag(context)
        
        # Classify intent with context and history (now returns multi-intent format)
        # Classify intent with context and history (now returns multi-intent format)
        trace.start_step("gemini_classification")
        classification = await self.classify_intent(
            message=message, 
            modules=enabled_modules, 
            context=context, 
            message_history=message_history,
            image_data=image_data
        )
        gemini_duration = trace._step_elapsed_ms()
        
        # Log Gemini Usage
        meta = classification.pop("_meta", None)
        if meta:
            trace.log_gemini_request(
                prompt="[System Prompt Hidden]", # Too long to log fully
                response_text=str(classification),
                model=meta.get("model"),
                prompt_tokens=meta.get("prompt_tokens"),
                response_tokens=meta.get("response_tokens")
            )
            
        trace.end_step("gemini_classification")
        
        # Extract reasoning for logging and tracing
        reasoning = classification.get("reasoning", "")
        logger.info(f"[{trace.trace_id}] AI Reasoning: {reasoning}")
        
        # Support both old single-intent and new multi-intent format
        intents_list = classification.get("intents", [])
        if not intents_list:
            # Fallback to old format for backward compatibility
            single_intent = classification.get("intent")
            if single_intent:
                intents_list = [{
                    "intent": single_intent,
                    "confidence": classification.get("confidence", 0.0),
                    "data": classification.get("data", {})
                }]
        
        # Log intent classification to trace
        trace.log_intent_classification(intents_list, reasoning)
        
        if not intents_list:
            trace.log_error("NoIntents", "Failed to classify any intents")
            return ModuleResponse(
                success=False,
                message=t("bot.unknown_intent", self.language)
            )
        
        # Process each intent and aggregate responses
        all_responses = []
        registry = get_registry()
        
        for intent_item in intents_list:
            intent = intent_item.get("intent", "unknown")
            confidence = intent_item.get("confidence", 0.0)
            data = intent_item.get("data", {})
            
            # Skip low confidence or unknown intents
            if intent == "unknown" or confidence < 0.3:
                trace.log_step(f"skip_intent_{intent}", {"confidence": confidence, "reason": "low_confidence"})
                continue
            
            trace.start_step(f"execute_{intent}")
            
            # Handle special intents
            if intent == "schedule_meeting" and confidence >= 0.5:
                resp = await self._handle_schedule_meeting(tenant_id, user_id, message, data)
                trace.log_module_execution("schedule_meeting", resp.success, resp.message)
                all_responses.append(resp.message)
                continue
            
            if intent == "recall" and confidence >= 0.5:
                resp = await self._handle_recall(tenant_id, message, context)
                trace.log_module_execution("recall", resp.success, resp.message)
                all_responses.append(resp.message)
                continue

            if intent == "cancel_meeting":
                msg = "Өкінішке орай, мен кездесулерді мәтін арқылы өшіре алмаймын." if self.language == "kz" else "К сожалению, я пока не умею удалять встречи через текст."
                trace.log_module_execution("cancel_meeting", False, msg, "Not implemented")
                all_responses.append(msg)
                continue
            
            # Find and execute module
            module = registry.get(intent)
            
            if not module:
                trace.end_step(f"execute_{intent}", error="Module not found")
                continue
            
            # Check if module is in enabled list
            if module not in enabled_modules:
                trace.end_step(f"execute_{intent}", error="Module not enabled")
                continue
            
            # Create module instance with DB session and process
            module_instance = type(module)(self.db)
            
            # Inject context and original message into data for modules that need it
            if context:
                data["rag_context"] = context
            
            # IMPORTANT: Always pass original message so modules can access raw user input
            data["original_message"] = message
            data["query"] = message  # Some modules use 'query' key
            
            try:
                response = await module_instance.process(
                    data, 
                    tenant_id, 
                    user_id, 
                    self.language
                )
                trace.log_module_execution(intent, response.success, response.message)
            except Exception as e:
                trace.log_module_execution(intent, False, None, str(e))
                response = ModuleResponse(success=False, message=f"Ошибка модуля {intent}: {str(e)}")
            
            # Always report result, even on failure (don't silently ignore errors)
            if response.message:
                all_responses.append(response.message)
            elif not response.success:
                # Module failed silently - inform user
                module_name = module.info.get_name(self.language)
                all_responses.append(f"⚠️ Не удалось выполнить: {module_name}")
        
        # Combine all responses
        if not all_responses:
            trace.log_error("NoResponses", "No modules produced a response")
            return ModuleResponse(
                success=False,
                message=t("bot.unknown_intent", self.language)
            )
        
        combined_message = "\n\n".join(all_responses)
        trace.set_final_response(combined_message, success=True)
        
        # Store conversation as memory (async, non-blocking)
        # 1. Store in Vector DB (RAG)
        await self._store_conversation_memory(
            tenant_id, user_id, message, combined_message
        )
        
        if not silent_response:
            # 2. Store in Relational DB (Chat History)
            try:
                from app.models.chat import Message
                
                # User message
                user_msg = Message(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    is_user=True,
                    content=message,
                    created_at=datetime.now()
                )
                self.db.add(user_msg)
                
                # Bot response (1 second later to ensure order)
                from datetime import timedelta
                bot_msg = Message(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    is_user=False,
                    content=combined_message,
                    intent=",".join([i.get("intent", "") for i in intents_list]),
                    created_at=datetime.now() + timedelta(seconds=1)
                )
                self.db.add(bot_msg)
                
                # We rely on the caller (TelegramBotService) to commit, or we can flush here
                await self.db.flush()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to save chat history: {e}")
        
        return ModuleResponse(success=True, message=combined_message)
    
    async def _handle_schedule_meeting(
        self,
        tenant_id: UUID,
        user_id: UUID,
        message: str,
        data: dict
    ) -> ModuleResponse:
        """Handle meeting scheduling with autonomous negotiation."""
        try:
            from app.services.meeting_negotiator import MeetingNegotiator
            from app.services.whatsapp_bot import WhatsAppBotService
            from app.models.tenant import Tenant
            
            # Get tenant for WhatsApp credentials
            tenant = await self.db.get(Tenant, tenant_id)
            if not tenant or not tenant.greenapi_instance_id:
                return ModuleResponse(
                    success=False,
                    message="Для согласования встреч нужна настройка WhatsApp."
                )
            
            whatsapp = WhatsAppBotService()
            negotiator = MeetingNegotiator(
                self.db, whatsapp, language=self.language
            )
            
            # Extract contact name and meeting title from data or message
            contact_name = data.get("contact_name") or data.get("attendee_name")
            meeting_title = data.get("meeting_title") or data.get("title", "Встреча")
            
            if not contact_name:
                # Try to extract from message
                # This is a simple extraction, AI should ideally do this
                return ModuleResponse(
                    success=False,
                    message="С кем хотите встретиться? Уточните имя контакта."
                )
            
            result = await negotiator.initiate_negotiation(
                tenant_id=tenant_id,
                initiator_user_id=user_id,
                contact_name=contact_name,
                meeting_title=meeting_title,
                whatsapp_instance_id=tenant.greenapi_instance_id,
                whatsapp_token=tenant.greenapi_token
            )
            
            if result.get("need_phone"):
                return ModuleResponse(
                    success=False,
                    message=result.get("message", "Контакт не найден.")
                )
            
            return ModuleResponse(
                success=True,
                message=result.get("message", "Отправил предложение о встрече.")
            )
            
        except Exception as e:
            return ModuleResponse(
                success=False,
                message=f"Ошибка при согласовании встречи: {str(e)}"
            )
    
    async def _handle_recall(
        self,
        tenant_id: UUID,
        message: str,
        context: str
    ) -> ModuleResponse:
        """Handle recall/memory query."""
        if not context:
            if self.language == "kz":
                return ModuleResponse(
                    success=True,
                    message="Өкінішке орай, осы тақырып бойынша ақпарат таппадым."
                )
            else:
                return ModuleResponse(
                    success=True,
                    message="К сожалению, не нашёл информации по этому вопросу в памяти."
                )
        
        # Use AI to format the context into a natural response
        if self.model:
            try:
                prompt = f"""
На основе найденной информации из памяти, ответь на вопрос пользователя.

Вопрос: {message}

Найденная информация:
{context}

Ответь кратко и по делу, цитируя источники.
"""
                response = self.model.generate_content(prompt)
                return ModuleResponse(
                    success=True,
                    message=response.text.strip()
                )
            except:
                pass
        
        # Fallback: return raw context
        if self.language == "kz":
            return ModuleResponse(
                success=True,
                message=f"Мен мынаны таптым:\n\n{context}"
            )
        else:
            return ModuleResponse(
                success=True,
                message=f"Вот что я нашёл:\n\n{context}"
            )
    
    async def _store_conversation_memory(
        self,
        tenant_id: UUID,
        user_id:Optional[ UUID ],
        user_message: str,
        bot_response: str
    ) -> None:
        """Store conversation as memory for future RAG queries."""
        try:
            from app.services.embedding_service import EmbeddingService
            
            embedding_service = EmbeddingService(self.db)
            await embedding_service.store_conversation_memory(
                tenant_id=tenant_id,
                user_message=user_message,
                bot_response=bot_response,
                user_id=user_id,
                source="chat"
            )
        except Exception:
            # Memory storage is optional, don't fail on error
            pass
