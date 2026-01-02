from __future__ import annotations
"""Base Agent class for Multi-Agent System."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from uuid import UUID
import logging

from pydantic import BaseModel, Field

from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
import google.generativeai as genai

logger = logging.getLogger(__name__)


class AgentTool(BaseModel):
    """Definition of a tool available to an agent."""
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable


class AgentResponse(BaseModel):
    """Standard response from an agent."""
    content: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract Base Agent.
    
    Attributes:
        db: Database session.
        tenant_id: Context tenant.
        user_id: Context user.
        model: GenerativeModel instance.
    """
    
    def __init__(
        self, 
        db: AsyncSession, 
        tenant_id: UUID, 
        user_id: Optional[UUID] = None,
        language: str = "ru",
        api_key: Optional[str] = None
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.language = language
        
        # Configure AI
        key = api_key or settings.gemini_api_key
        if key:
            genai.configure(api_key=key)
            self.model = genai.GenerativeModel(settings.gemini_model)
        else:
            self.model = None
            logger.warning(f"Agent {self.__class__.__name__} initialized without API Key")

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name."""
        pass

    @property
    @abstractmethod
    def role_description(self) -> str:
        """High-level description of what this agent does."""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Construct the system prompt for this agent."""
        pass

    @abstractmethod
    def get_tools(self) -> List[AgentTool]:
        """Return list of tools available to this agent."""
        pass

    async def run(self, message: str, context: Optional[str] = None) -> AgentResponse:
        """
        Execute the agent logic using Gemini Function Calling.
        
        1. Build prompt (System + Context + User Message).
        2. Call LLM with tools.
        3. Parse result (Content or Tool Calls).
        """
        if not self.model:
            return AgentResponse(content="AI key missing.")

        system_prompt = self.get_system_prompt()
        user_prompt = f"Context:\n{context}\n\nUser: {message}" if context else message

        # Build tools for Gemini
        agent_tools = self.get_tools()
        
        try:
            # If agent has tools, use function calling
            if agent_tools:
                # Convert our AgentTool to Gemini format
                function_declarations = []
                for tool in agent_tools:
                    function_declarations.append({
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": {
                            "type": "object",
                            "properties": tool.parameters if tool.parameters else {},
                            "required": []
                        }
                    })
                
                gemini_tools = [{"function_declarations": function_declarations}]
                
                # Tool config for constrained decoding
                from google.generativeai.types import content_types
                tool_config = content_types.to_tool_config({
                    "function_calling_config": {"mode": "AUTO"}
                })
                
                response = self.model.generate_content(
                    [
                        {"role": "user", "parts": [system_prompt]},
                        {"role": "model", "parts": ["Ready."]},
                        {"role": "user", "parts": [user_prompt]}
                    ],
                    tools=gemini_tools,
                    tool_config=tool_config
                )
            else:
                # No tools, simple generation
                response = self.model.generate_content([
                    {"role": "user", "parts": [system_prompt]},
                    {"role": "model", "parts": ["Ready."]},
                    {"role": "user", "parts": [user_prompt]}
                ])
            
            # Parse response
            candidate = response.candidates[0]
            part = candidate.content.parts[0]
            
            # Check if it's a function call
            if hasattr(part, 'function_call') and part.function_call:
                func_call = part.function_call
                return AgentResponse(
                    content="",
                    tool_calls=[{
                        "name": func_call.name,
                        "args": dict(func_call.args) if func_call.args else {}
                    }]
                )
            
            # Otherwise it's text
            # Otherwise it's text, but check if it contains "Action:" pattern (CoT fallback)
            content_text = response.text
            import re
            action_match = re.search(r"Action:\s*([\w_]+)", content_text)
            
            if action_match:
                tool_name = action_match.group(1).strip()
                logger.info(f"detected text-based action: {tool_name}")
                return AgentResponse(
                    content=content_text, # Keep thought process
                    tool_calls=[{
                        "name": tool_name,
                        "args": {} # Text actions usually don't have args in this current prompt format, or strict CoT implies handoff
                    }]
                )

            return AgentResponse(content=content_text)
            
        except Exception as e:
            logger.error(f"Agent {self.name} error: {e}")
            # Fallback: try simple generation without tools
            try:
                response = self.model.generate_content([
                    {"role": "user", "parts": [system_prompt]},
                    {"role": "model", "parts": ["Ready."]},
                    {"role": "user", "parts": [user_prompt]}
                ])
                return AgentResponse(content=response.text)
            except Exception as e2:
                return AgentResponse(content=f"Error: {e2}")
