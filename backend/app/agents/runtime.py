from __future__ import annotations
from typing import List, Dict, Any, Optional, Callable, Awaitable
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, AgentResponse
from app.agents.chief import ChiefOfStaffAgent
from app.agents.finance import FinanceAgent
from app.agents.calendar import CalendarAgent
from app.agents.tasks import TasksAgent
from app.agents.contacts import ContactsAgent
from app.agents.birthday import BirthdayAgent
from app.agents.ideas import IdeasAgent
from app.agents.debtor import DebtorAgent
from app.agents.knowledge import KnowledgeAgent
from app.agents.travel import TravelAgent
import logging

logger = logging.getLogger(__name__)

# Callback type: async function that takes a string message
StatusCallback = Callable[[str], Awaitable[None]]

class AgentRuntime:
    """
    The Loop. Handles agent execution and hand-offs.
    Supports Inter-Agent Communication for complex multi-step tasks.
    """
    
    def __init__(
        self, 
        db: AsyncSession, 
        tenant_id: UUID, 
        user_id: Optional[UUID] = None,
        language: str = "ru"
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.language = language
        
        # Initialize all agents
        self.agents: Dict[str, BaseAgent] = {
            "chief": ChiefOfStaffAgent(db, tenant_id, user_id, language),
            "finance_agent": FinanceAgent(db, tenant_id, user_id, language),
            "calendar_agent": CalendarAgent(db, tenant_id, user_id, language),
            "tasks_agent": TasksAgent(db, tenant_id, user_id, language),
            "contacts_agent": ContactsAgent(db, tenant_id, user_id, language),
            "birthday_agent": BirthdayAgent(db, tenant_id, user_id, language),
            "ideas_agent": IdeasAgent(db, tenant_id, user_id, language),
            "debtor_agent": DebtorAgent(db, tenant_id, user_id, language),
            "knowledge_agent": KnowledgeAgent(db, tenant_id, user_id, language),
            "travel_agent": TravelAgent(db, tenant_id, user_id, language),
        }
        
        # Handoff map
        self.handoff_map = {
            "transfer_to_finance": "finance_agent",
            "transfer_to_calendar": "calendar_agent",
            "transfer_to_tasks": "tasks_agent",
            "transfer_to_contacts": "contacts_agent",
            "transfer_to_birthday": "birthday_agent",
            "transfer_to_ideas": "ideas_agent",
            "transfer_to_debtor": "debtor_agent",
            "transfer_to_knowledge": "knowledge_agent",
            "transfer_to_travel": "travel_agent",
        }
    
    async def execute_agent_tool(
        self, 
        agent_name: str, 
        tool_name: str, 
        tool_args: Dict[str, Any]
    ) -> str:
        """
        Execute a specific tool on a specific agent.
        Used for Inter-Agent Communication.
        """
        # Normalize agent name with alias mapping
        agent_aliases = {
            "calendar": "calendar_agent",
            "tasks": "tasks_agent",
            "finance": "finance_agent",
            "contacts": "contacts_agent",
            "birthday": "birthday_agent",
            "birthdays": "birthday_agent",
            "ideas": "ideas_agent",
            "debtor": "debtor_agent",
            "debtors": "debtor_agent",
            "knowledge": "knowledge_agent",
            "travel": "travel_agent",
        }
        normalized_name = agent_aliases.get(agent_name.lower(), agent_name)
        
        agent = self.agents.get(normalized_name)
        if not agent:
            return f"❌ Агент '{agent_name}' не найден"
        
        # Normalize tool name with alias mapping
        tool_aliases = {
            "getevents": "get_today_meetings",
            "get_events": "get_today_meetings",
            "gettasks": "get_all_tasks",
            "get_tasks": "get_all_tasks",
            "getmeetings": "get_today_meetings",
            "get_meetings": "get_today_meetings",
            "getcontacts": "get_all_contacts",
            "get_contacts": "get_all_contacts",
            "getbalance": "get_balance",
        }
        normalized_tool = tool_aliases.get(tool_name.lower(), tool_name)
        
        for tool in agent.get_tools():
            if tool.name == normalized_tool:
                try:
                    result = await tool.function(**tool_args)
                    return result
                except TypeError as e:
                    # Missing or wrong parameters
                    logger.error(f"Tool {tool_name} parameter error: {e}")
                    return f"❌ Неверные параметры для {tool_name}: {str(e).split(':')[-1].strip()}"
                except Exception as e:
                    logger.error(f"Inter-agent tool {tool_name} error: {e}")
                    # User-friendly error messages
                    err_msg = str(e)
                    if "UNIQUE constraint" in err_msg:
                        return f"❌ Такая запись уже существует"
                    elif "NOT NULL" in err_msg:
                        return f"❌ Не заполнены обязательные поля"
                    elif "invalid keyword" in err_msg:
                        param = err_msg.split("'")[1] if "'" in err_msg else "?"
                        return f"❌ Неизвестный параметр: {param}"
                    else:
                        return f"❌ Ошибка: {err_msg[:100]}"
        
        return f"❌ Инструмент '{tool_name}' не найден у агента '{agent_name}'"
    
    async def _execute_step(self, step) -> str:
        """
        Parse and execute a step.
        Formats supported:
        1. JSON dict: {"agent": "name", "tool": "name", "params": {...}}
        2. String: "agent_name.tool_name(param1=value1)"
        3. String: "agent_name:tool_name:param1=val1"
        """
        import re
        import json
        
        # Format 1: JSON dict (preferred, most robust)
        if isinstance(step, dict):
            agent_name = step.get("agent", "")
            tool_name = step.get("tool", "")
            params = step.get("params", {})
            
            # Smart casting
            clean_params = {}
            for k, v in params.items():
                if isinstance(v, str):
                    if v.isdigit():
                        clean_params[k] = int(v)
                    elif v.replace('.', '', 1).isdigit() and v.count('.') < 2:
                        clean_params[k] = float(v)
                    else:
                        clean_params[k] = v
                else:
                    clean_params[k] = v
            
            if agent_name and tool_name:
                return await self.execute_agent_tool(agent_name, tool_name, clean_params)
            return f"❌ Неверный JSON формат: {step}"
        
        # Format 1b: JSON string
        if isinstance(step, str) and step.strip().startswith("{"):
            try:
                step_dict = json.loads(step)
                agent_name = step_dict.get("agent", "")
                tool_name = step_dict.get("tool", "")
                params = step_dict.get("params", {})
                
                # Smart casting
                clean_params = {}
                for k, v in params.items():
                    if isinstance(v, str):
                        if v.isdigit():
                            clean_params[k] = int(v)
                        elif v.replace('.', '', 1).isdigit() and v.count('.') < 2:
                            clean_params[k] = float(v)
                        else:
                            clean_params[k] = v
                    else:
                        clean_params[k] = v
                
                if agent_name and tool_name:
                    return await self.execute_agent_tool(agent_name, tool_name, clean_params)
            except json.JSONDecodeError:
                pass  # Fall through to string formats
        
        # Format 2: agent.tool(args)
        if isinstance(step, str):
            match = re.match(r'(\w+)\.(\w+)\((.*)\)', step)
            if match:
                agent_name = match.group(1)
                tool_name = match.group(2)
                args_str = match.group(3)
                
                args = {}
                if args_str:
                    for part in re.findall(r'(\w+)=["\']?([^,"\']+)["\']?', args_str):
                        key, val = part
                        try:
                            args[key] = float(val) if '.' in val else int(val)
                        except:
                            args[key] = val
                
                return await self.execute_agent_tool(agent_name, tool_name, args)
            
            # Format 3: agent:tool:args
            parts = step.split(":")
            if len(parts) >= 2:
                agent_name = parts[0]
                tool_name = parts[1]
                args = {}
                
                if len(parts) >= 3:
                    for pair in parts[2].split(","):
                        if "=" in pair:
                            key, val = pair.split("=", 1)
                            try:
                                args[key.strip()] = float(val) if '.' in val else int(val)
                            except:
                                args[key.strip()] = val.strip()
                
                return await self.execute_agent_tool(agent_name, tool_name, args)
        
        return f"❌ Неизвестный формат шага: {step}"
    
    def _inject_context(self, step: dict, context: dict) -> dict:
        """
        Inject context from previous steps into step params.
        Replaces placeholders like {{phone}} with actual values.
        """
        import copy
        step = copy.deepcopy(step)
        
        params = step.get("params", {})
        for key, value in params.items():
            if isinstance(value, str):
                # Replace context placeholders
                for ctx_key, ctx_val in context.items():
                    placeholder = f"{{{{{ctx_key}}}}}"
                    if placeholder in value:
                        params[key] = value.replace(placeholder, str(ctx_val))
                
                # Auto-inject phone if param is 'phone' and empty
                if key == "phone" and not value and "phone" in context:
                    params[key] = context["phone"]
        
        step["params"] = params
        return step
        
    async def run(
        self, 
        user_message: str, 
        history: List[Dict[str, str]] = None,
        on_status: Optional[StatusCallback] = None
    ) -> str:
        """
        Main Loop.
        Starts with Chief, follows hand-offs until a text reply is generated.
        Supports Inter-Agent Communication for complex tasks.
        """
        current_agent_name = "chief"
        
        # Limit loop to prevent infinite hops
        max_hops = 10  # Increased for inter-agent chains
        hops = 0
        
        # Context for multi-step processing
        context_messages = history or []
        accumulated_results = []  # Store results from inter-agent calls
        
        while hops < max_hops:
            current_agent = self.agents.get(current_agent_name)
            if not current_agent:
                return "Error: Agent not found."
            
            logger.info(f"🤖 Active Agent: {current_agent.name}")
            
            if on_status:
                await on_status(f"🤖 Agent: {current_agent.name} working...")
            
            # Build context with accumulated results (use last 100 messages for better memory)
            context_parts = [f"{m['role']}: {m['content']}" for m in context_messages[-100:]]
            if accumulated_results:
                context_parts.append(f"Previous results: {'; '.join(accumulated_results)}")
            context_str = "\n".join(context_parts)
            
            response: AgentResponse = await current_agent.run(
                message=user_message,
                context=context_str
            )
            
            # Check for Function Calls
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("args", {})
                    
                    # 1. Check for handoff
                    target = self.handoff_map.get(tool_name)
                    if target and target in self.agents:
                        logger.info(f"🔄 Handoff: {current_agent_name} -> {target}")
                        if on_status:
                            await on_status(f"🔄 Handoff: {current_agent_name} -> {target}")
                        current_agent_name = target
                        hops += 1
                        break
                    
                    # 2. Check for inter-agent call (call_agent:agent_name:tool_name)
                    if tool_name.startswith("call_agent:"):
                        parts = tool_name.split(":")
                        if len(parts) >= 3:
                            target_agent = parts[1]
                            target_tool = parts[2]
                            logger.info(f"📞 Inter-Agent Call: {current_agent_name} -> {target_agent}.{target_tool}")
                            if on_status:
                                await on_status(f"📞 Calling {target_agent}.{target_tool}...")
                            
                            result = await self.execute_agent_tool(target_agent, target_tool, tool_args)
                            accumulated_results.append(f"{target_tool}: {result}")
                            hops += 1
                            continue
                    
                    # 3. Execute tool on current agent
                    logger.info(f"🔧 Executing tool: {tool_name}")
                    if on_status:
                        await on_status(f"🔧 Executing: {tool_name}")
                    
                    for agent_tool in current_agent.get_tools():
                        if agent_tool.name == tool_name:
                            try:
                                result = await agent_tool.function(**tool_args)
                                
                                # Check if result needs follow-up action
                                # Pattern: "CALL_AGENT:agent:tool:args"
                                if isinstance(result, str) and result.startswith("CALL_AGENT:"):
                                    parts = result.split(":", 3)
                                    if len(parts) >= 4:
                                        target_agent = parts[1]
                                        target_tool = parts[2]
                                        import json
                                        follow_args = json.loads(parts[3]) if parts[3] else {}
                                        
                                        logger.info(f"📞 Follow-up call: {target_agent}.{target_tool}")
                                        if on_status:
                                            await on_status(f"📞 Follow-up: {target_agent}.{target_tool}...")
                                        
                                        follow_result = await self.execute_agent_tool(
                                            target_agent, target_tool, follow_args
                                        )
                                        return follow_result
                                
                                # Pattern: "SEARCH_AND_SAVE|query|name" for search + save contact
                                if isinstance(result, str) and result.startswith("SEARCH_AND_SAVE|"):
                                    import re
                                    
                                    parts = result.split("|")
                                    if len(parts) >= 3:
                                        search_query = parts[1]
                                        contact_name = parts[2]
                                        
                                        logger.info(f"🔍 Step 1: Searching for {search_query}")
                                        if on_status:
                                            await on_status(f"🔍 Searching: {search_query}...")
                                        
                                        # Step 1: Search using Knowledge Agent
                                        knowledge_agent = self.agents.get("knowledge_agent")
                                        if knowledge_agent:
                                            search_response = await knowledge_agent.run(
                                                message=f"Найди телефон {search_query}",
                                                context=""
                                            )
                                            search_result = search_response.content
                                            
                                            # Extract phone number
                                            phone_match = re.search(r'\+?[\d\s\-\(\)]{10,}', search_result)
                                            phone_number = phone_match.group(0).replace(" ", "").replace("-", "") if phone_match else None
                                            
                                            if phone_number:
                                                logger.info(f"📞 Step 2: Saving contact {contact_name}: {phone_number}")
                                                if on_status:
                                                    await on_status(f"💾 Saving: {contact_name}...")
                                                
                                                # Step 2: Save contact
                                                save_result = await self.execute_agent_tool(
                                                    "contacts_agent",
                                                    "create_contact",
                                                    {"name": contact_name, "phone": phone_number}
                                                )
                                                
                                                return f"🔍 Найдено: {phone_number}\n\n{save_result}"
                                            else:
                                                return f"🔍 Результат поиска:\n{search_result}\n\n❌ Номер телефона не найден в результатах"
                                        
                                        return "Error: Knowledge agent not found"
                                
                                # Pattern: "MULTI_TASK:[...]" for universal multi-step
                                if isinstance(result, str) and result.startswith("MULTI_TASK:"):
                                    import json
                                    import re
                                    
                                    steps_json = result[11:]  # Remove "MULTI_TASK:"
                                    try:
                                        steps = json.loads(steps_json)
                                    except Exception as e:
                                        logger.error(f"Failed to parse MULTI_TASK: {e}")
                                        return f"❌ Ошибка разбора задач: {e}"
                                    
                                    all_results = []
                                    step_context = {}  # Pass context between steps
                                    
                                    for i, step in enumerate(steps, 1):
                                        logger.info(f"📋 Step {i}/{len(steps)}: {step}")
                                        if on_status:
                                            await on_status(f"📋 Шаг {i}/{len(steps)}...")
                                        
                                        # Inject context from previous steps into params
                                        if isinstance(step, dict) and step_context:
                                            step = self._inject_context(step, step_context)
                                        
                                        # Execute with retry
                                        step_result = None
                                        for attempt in range(2):  # Max 2 attempts
                                            step_result = await self._execute_step(step)
                                            if not step_result.startswith("❌"):
                                                break  # Success
                                            logger.warning(f"Step {i} attempt {attempt+1} failed: {step_result}")
                                        
                                        # Store result in context for next steps
                                        step_context[f"step_{i}_result"] = step_result
                                        
                                        # Extract useful data from result
                                        phone_match = re.search(r'\+?[\d]{10,}', step_result)
                                        if phone_match:
                                            step_context["phone"] = phone_match.group(0)
                                        
                                        all_results.append(f"✅ Шаг {i}: {step_result}")
                                    
                                    return "\n\n".join(all_results)
                                
                                return result
                            except Exception as e:
                                logger.error(f"Tool {tool_name} error: {e}")
                                return f"Error executing {tool_name}: {e}"
                    
                    return f"Tool '{tool_name}' not found on {current_agent.name}"
                else:
                    continue
                continue
            
            content = response.content.strip()
            
            # Fallback: Check for text-based handoff signal
            if "handoff:" in content:
                target = content.split("handoff:")[1].strip()
                if target in self.agents:
                    logger.info(f"🔄 Handoff (Text): {current_agent_name} -> {target}")
                    if on_status:
                        await on_status(f"🔄 Handoff: {current_agent_name} -> {target}")
                    current_agent_name = target
                    hops += 1
                    continue
            
            # If there are accumulated results, append them to response
            if accumulated_results:
                content += "\n\n" + "\n".join(accumulated_results)
            
            # If no handoff, return the response to user
            return content
            
        return "System limit reached (too many agent hops)."

