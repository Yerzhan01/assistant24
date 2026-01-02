from __future__ import annotations
from typing import List, Optional
from app.agents.base import BaseAgent, AgentTool
from sqlalchemy import select
from app.models.idea import Idea
from app.services.perplexity import PerplexityClient

class IdeasAgent(BaseAgent):
    """Ideas Agent & Copywriter. Manages business ideas and writes content."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.writer = PerplexityClient()
    
    @property
    def name(self) -> str:
        return "IdeasAgent"

    @property
    def role_description(self) -> str:
        return "You are the Creative Director. You manage ideas and write professional content (Instagram, LinkedIn, etc)."

    def get_system_prompt(self) -> str:
        return f"""
        Ты — Агент Идей и Креативный Копирайтер.
        
        ТВОИ ЗАДАЧИ:
        1. 💡 **Управление идеями**: Сохраняй (`create_idea`) и показывай (`get_all_ideas`).
        2. ✍️ **Написание постов**: Если пользователь просит "напиши пост", "сделай текст" — используй `write_post`.
           - Ты умеешь писать для Instagram, Telegram, LinkedIn.
           - Ты добавляешь хэштеги и структуру.
        
        Язык: {self.language}
        """

    def get_tools(self) -> List[AgentTool]:
        return [
            AgentTool(
                name="get_all_ideas",
                description="Получить список всех идей.",
                parameters={},
                function=self._get_all_ideas
            ),
            AgentTool(
                name="create_idea",
                description="Сохранить новую идею.",
                parameters={"title": {"type": "string", "description": "Текст идеи"}},
                function=self._create_idea
            ),
            AgentTool(
                name="write_post",
                description="Написать пост/текст на основе идеи или темы.",
                parameters={
                    "topic": {"type": "string", "description": "Тема поста или идея"},
                    "platform": {"type": "string", "description": "Платформа (Instagram, Telegram, LinkedIn, Email)"},
                    "tone": {"type": "string", "description": "Тон (продающий, личный, экспертный)"}
                },
                function=self._write_post
            ),
        ]
        
    async def _get_all_ideas(self) -> str:
        stmt = select(Idea).where(Idea.tenant_id == self.tenant_id).limit(10)
        result = await self.db.execute(stmt)
        ideas = result.scalars().all()
        
        if ideas:
            lines = ["💡 **Ваши идеи:**"]
            for i in ideas:
                priority_emoji = "🔥" if i.priority == "high" else "🔸"
                lines.append(f"{priority_emoji} {i.title}")
            
            lines.append("\n*Совет: Выберите идею и скажите 'Напиши пост про это'*")
            return "\n".join(lines)
        return "💡 Идей пока нет. Скажите 'Запиши идею...'"
    
    async def _create_idea(self, title: str = "") -> str:
        if not title:
            return "❌ Укажите текст идеи"
        
        idea = Idea(
            tenant_id=self.tenant_id,
            title=title,
            priority="medium",
            status="new"
        )
        self.db.add(idea)
        await self.db.commit()
        
        return f"✅ **Идея сохранена:** \"{title}\"\nХотите я напишу пост про это? (Скажите 'Напиши пост')"
    
    async def _write_post(self, topic: str, platform: str = "Instagram", tone: str = "Expert") -> str:
        """Generate a post using Perplexity."""
        
        prompt = f"""
        Act as a professional Copywriter. Write a post about "{topic}".
        Platform: {platform}
        Tone: {tone}
        Language: Russian (but use English terms if relevant for tech).
        
        Structure:
        1. Catchy Headline (Hook)
        2. Body (Engaging value)
        3. Call to Action (CTA)
        4. Hashtags
        
        Make it viral and high quality.
        """
        
        result = await self.writer.search(
            query=prompt,
            system_prompt="You are a world-class Copywriter. Output ONLY the post content, no conversational filler."
        )
        
        return f"""✍️ **Черновик поста ({platform}):**
        
{result}

📝 *Могу переписать, если скажешь "сделай короче" или "добавь юмора".*"""


