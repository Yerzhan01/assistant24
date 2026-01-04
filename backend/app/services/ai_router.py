from __future__ import annotations
"""AI Router - Intent classification and data extraction using Google Gemini with RAG."""
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Callable, Awaitable
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
            
            # Configuration for Intent Classification (Strict JSON)
            # Temperature 0.0 for reproducibility
            # Disable thoughts to prevent JSON corruption
            generation_config = {
                "temperature": 0.0,
                "top_p": 0.8,
                "top_k": 40,
                # "thinking_config": {"include_thoughts": False} # Explicitly disable if supported, or omit
            }

            self.model = genai.GenerativeModel(
                settings.gemini_model,
                generation_config=generation_config
            )
        else:
            self.model = None
    
    def _safe_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Safely parse JSON from Gemini response.
        Handles markdown code blocks, malformed JSON, and missing fields.
        Robustly extracts { ... } from text.
        """
        if not text:
            return None
            
        import re
        
        # 1. Clean Markdown
        clean_text = text.strip()
        if "```" in clean_text:
            # Extract content strictly between first ```(json)? and last ```
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text)
            if match:
                clean_text = match.group(1).strip()
        
        # 2. Extract JSON object if text contains extra chatter
        # Look for first '{' and last '}'
        start = clean_text.find("{")
        end = clean_text.rfind("}")
        
        if start != -1 and end != -1:
            clean_text = clean_text[start:end+1]
        elif start != -1: # Maybe missing closing brace?
            clean_text = clean_text[start:] + "}" # Attempt repair
            
        # 3. Try parsing
        try:
            result = json.loads(clean_text)
            
            # Validate required structure
            if not isinstance(result, dict):
                logger.warning(f"Gemini returned non-dict JSON: {type(result)}")
                return None
            
            # Ensure 'intents' exists (normalize single intent)
            if "intents" not in result or not isinstance(result.get("intents"), list):
                if "intent" in result:
                    result = {
                        "reasoning": result.get("reasoning", "Normalized single intent"),
                        "intents": [result]
                    }
                else:
                    logger.warning(f"Gemini returned JSON without intents: {result}")
                    return None
            
            # Validate intents
            valid_intents = []
            for intent in result.get("intents", []):
                if isinstance(intent, dict) and intent.get("intent"):
                    valid_intents.append(intent)
            
            if not valid_intents:
                return None
                
            result["intents"] = valid_intents
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e} | Text: {clean_text[:200]}")
            return None
    
    def _apply_whatsapp_priority(self, message: str, result: Dict[str, Any], modules: List[BaseModule]) -> Dict[str, Any]:
        """
        Check if message clearly indicates WhatsApp intent.
        If so, override Gemini's classification to ensure correct routing.
        """
        message_lower = message.lower().strip()
        
        # WhatsApp-specific keywords that MUST route to WhatsApp
        wa_strong_keywords = [
            "напиши в ватсап", "напиши в whatsapp", "напиши в уатсап",
            "отправь в ватсап", "отправь в whatsapp", "отправь в уатсап",
            "напиши ему", "напиши ей", "напиши ему в уатсап",
            "через уатсап", "через ватсап", "через whatsapp"
        ]
        
        # Check for strong keywords first
        for kw in wa_strong_keywords:
            if kw in message_lower:
                logger.info(f"WhatsApp priority override triggered by keyword: {kw}")
                return self._force_whatsapp_intent(message, result)
        
        return result
    
    def _force_whatsapp_intent(self, message: str, original_result: Dict[str, Any]) -> Dict[str, Any]:
        """Force WhatsApp intent with original message for further processing."""
        return {
            "reasoning": f"WhatsApp priority override. Original: {original_result.get('reasoning', 'N/A')}",
            "intents": [{
                "intent": "whatsapp",
                "confidence": 0.95,
                "data": {
                    "action": "send_message",
                    "original_message": message
                }
            }],
            "_meta": original_result.get("_meta", {})
        }

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
        Uses system_instruction for cleaner separation of roles.
        """
        module_ids = [m.module_id for m in modules]
        logger.info(f"Classifying intent with modules: {module_ids} for message: {message[:50]}...")
        
        system_prompt = self._build_system_prompt(modules, context, message_history)
        
        # Instantiate model with system instruction (Per-request instance)
        # This is cheap and ensures clean context without mixing roles in history
        config = {
            "temperature": 0.0,
            "top_p": 0.8,
            "top_k": 40
        }
        
        try:
            # Use instance model or create new one if system instruction supported (0.8.3+)
            model = genai.GenerativeModel(
                settings.gemini_model,
                system_instruction=system_prompt,
                generation_config=config
            )
            
            # Prepare User Input
            user_parts = [message]
            
            if image_data:
                # Add Vision Instruction
                user_parts[0] = f"""
                [IMAGE UPLOADED]
                Пользователь отправил фото.
                1. Проанализируй изображение (чек, счет, документ?).
                2. Извлеки СУММУ, ДАТУ, КАТЕГОРИЮ.
                3. Если чек -> intent: 'expense'.
                4. Если просто фото -> опиши.
                Текущий текст: {message}
                """
                try:
                    image_part = {"mime_type": "image/jpeg", "data": image_data}
                    user_parts.append(image_part)
                except Exception as e:
                    logger.error(f"Failed to attach image: {e}")

            # Generate (Single turn, no history needed as it's in system prompt)
            response = await model.generate_content_async(user_parts)
            
            text = response.text.strip()
            logger.info(f"Gemini Raw Response: {text}")
            
            result = self._safe_parse_json(text)
            
            if result is None:
                logger.warning("Safe JSON parsing failed, using fallback classification")
                return self._fallback_classify(message, modules)
            
            # Metadata
            if hasattr(response, "usage_metadata"):
                result["_meta"] = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "response_tokens": response.usage_metadata.candidates_token_count,
                    "model": settings.gemini_model
                }
            
            # Override
            result = self._apply_whatsapp_priority(message, result, modules)
            return result
            
        except Exception as e:
            logger.error(f"Gemini classification error: {e}")
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
        Process a user message end-to-end (Unified Pipeline 2.0).
        1. Setup Tracing
        2. Get Context & History
        3. Classify Intent
        4. Execute Modules
        5. Save History
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
            # 1. Get Enabled Modules
            trace.start_step("get_modules")
            if not enabled_modules:
                registry = get_registry()
                enabled_modules = await registry.get_enabled_modules(self.db, tenant_id)
            
            if not enabled_modules:
                trace.log_error("NoModules", "No enabled modules found")
                return ModuleResponse(success=False, message=t("bot.error", self.language))
            trace.end_step("get_modules", {"count": len(enabled_modules)})

            # 2. Get History (Last 5 messages)
            message_history = []
            trace.start_step("get_history")
            try:
                from sqlalchemy import select, desc
                from app.models.chat import Message as ChatMessageModel # Renamed from Message to avoid conflict if any
                
                # Fetch recent history for context
                stmt = select(ChatMessageModel).where(
                    ChatMessageModel.tenant_id == tenant_id
                ).order_by(desc(ChatMessageModel.created_at)).limit(5)
                
                result = await self.db.execute(stmt)
                db_msgs = result.scalars().all()
                for m in reversed(db_msgs):
                    message_history.append({
                        "role": "user" if m.is_user else "assistant", 
                        "content": m.content
                    })
                trace.end_step("get_history", {"count": len(message_history)})
            except Exception as e:
                trace.log_step("get_history_error", error=str(e))
                trace.end_step("get_history", {"error": str(e)})

            # 3. RAG Retrieval
            trace.start_step("rag_retrieval")
            context = await self.get_rag_context(tenant_id, message)
            trace.end_step("rag_retrieval", {"length": len(context)})
            trace.log_rag(context)
            
            # 4. Classification
            if on_status: await on_status("Thinking...")
            trace.start_step("classify")
            classification = await self.classify_intent(
                message, enabled_modules, context, message_history, image_data
            )
            
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
            trace.end_step("classify")

            # Log reasoning
            reasoning = classification.get("reasoning", "")
            intents = classification.get("intents", [])
            trace.log_intent_classification(intents, reasoning)
            logger.info(f"[{trace.trace_id}] AI Reasoning: {reasoning}")
            
            if not intents:
                return ModuleResponse(success=False, message=t("bot.unknown_intent", self.language))

            # 5. Execution
            if on_status: await on_status("Executing...")
            all_responses = []
            registry = get_registry()
            for item in intents:
                intent = item.get("intent")
                data = item.get("data", {})
                confidence = item.get("confidence", 0.0)
                
                # Skip low confidence
                if confidence < 0.3: continue
                
                trace.start_step(f"exec_{intent}")
                
                # Special Handlers
                if intent == "recall":
                    resp = await self._handle_recall(tenant_id, message, context)
                    all_responses.append(resp.message)
                    trace.end_step(f"exec_{intent}", {"status": "recall_done"})
                    continue
                    
                if intent == "cancel_meeting":
                    msg = "Функция отмены встреч пока недоступна."
                    all_responses.append(msg)
                    continue

                # Module Execution
                module = registry.get(intent)
                if module and module in enabled_modules:
                    instance = type(module)(self.db)
                    
                    # Inject context
                    data["rag_context"] = context
                    data["original_message"] = message
                    
                    try:
                        resp = await instance.process(data, tenant_id, user_id, self.language)
                        if resp.message:
                            all_responses.append(resp.message)
                        elif not resp.success:
                             all_responses.append(f"⚠️ Ошибка модуля {intent}")
                    except Exception as e:
                        logger.error(f"Module {intent} failed: {e}")
                        all_responses.append(f"❌ Ошибка: {str(e)}")
                
                trace.end_step(f"exec_{intent}")

            # 6. Finalize Response
            combined_message = "\n\n".join(all_responses)
            if not combined_message:
                 combined_message = t("bot.unknown_intent", self.language)

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
                        intent="user_input",
                        created_at=datetime.now()
                    )
                    self.db.add(user_msg)
                    
                    # Dual-Write: Unified Interaction (User)
                    from app.models.interaction import UnifiedInteraction, InteractionSource, InteractionRole
                    user_interaction = UnifiedInteraction(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        session_id=f"web:{user_id or 'anon'}",
                        source=InteractionSource.WEB.value,
                        role=InteractionRole.USER.value,
                        content=message,
                        metadata_={"intent": "user_input"},
                        created_at=user_msg.created_at
                    )
                    self.db.add(user_interaction)
                    
                    # Bot response (1 second later to ensure order)
                    from datetime import timedelta
                    bot_msg = Message(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        is_user=False,
                        content=combined_message,
                        intent=",".join([i.get("intent", "") for i in intents]),
                        created_at=datetime.now() + timedelta(seconds=1)
                    )
                    self.db.add(bot_msg)
                    
                    # Dual-Write: Unified Interaction (Bot)
                    bot_interaction = UnifiedInteraction(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        session_id=f"web:{user_id or 'anon'}",
                        source=InteractionSource.WEB.value,
                        role=InteractionRole.ASSISTANT.value,
                        content=combined_message,
                        metadata_={"intents": intents},
                        created_at=bot_msg.created_at
                    )
                    self.db.add(bot_interaction)
                    
                    # We rely on the caller (TelegramBotService) to commit, or we can flush here
                    await self.db.flush()
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Failed to save chat history: {e}")
            
            return ModuleResponse(success=True, message=combined_message)

        except Exception as e:
            trace.log_error("CriticalPipelineError", str(e))
            return ModuleResponse(success=False, message=f"Системная ошибка: {str(e)}")
        finally:
            await trace.save()
    
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
