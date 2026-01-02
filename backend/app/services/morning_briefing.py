from __future__ import annotations
"""Morning Briefing service for daily digest notifications."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

import google.generativeai as genai
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.meeting import Meeting, MeetingStatus
from app.models.task import Task, TaskStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.tenant import Tenant
from app.models.finance import FinanceRecord

logger = logging.getLogger(__name__)


BRIEFING_PROMPT_RU = """
Сгенерируй утренний брифинг для предпринимателя. Тон дружелюбный и мотивирующий.

Имя пользователя: {user_name}
Текущая дата: {date}

Данные дня:
- Встречи сегодня: {meetings}
- Горящие дедлайны: {overdue_tasks}
- Задачи на сегодня: {today_tasks}
- Просроченные оплаты: {overdue_invoices}
- Финансы вчера: доход {income} ₸, расход {expense} ₸, итого {balance_change}

Правила:
- Начни с приветствия "Доброе утро, {user_name}! ☕️"
- Используй эмодзи для разделов: 📅 встречи, 🔥 горящие, ✅ задачи, 💰 финансы
- Если нет встреч — напиши что день свободен для работы
- Если есть просроченные — обязательно отметь
- Заверши мотивирующей фразой
- Максимум 10-15 строк

Верни текст брифинга.
"""

BRIEFING_PROMPT_KZ = """
Кәсіпкерге таңғы брифинг жаса. Достық және мотивациялық үн.

Пайдаланушы аты: {user_name}
Ағымдағы күн: {date}

Күн деректері:
- Бүгінгі кездесулер: {meetings}
- Мерзімі өткен тапсырмалар: {overdue_tasks}
- Бүгінгі тапсырмалар: {today_tasks}
- Мерзімі өткен төлемдер: {overdue_invoices}
- Кешегі қаржы: кіріс {income} ₸, шығыс {expense} ₸, қорытынды {balance_change}

Ережелер:
- "Қайырлы таң, {user_name}! ☕️" деп бастал
- Бөлімдерге эмодзи қолдан: 📅 кездесулер, 🔥 шұғыл, ✅ тапсырмалар, 💰 қаржы
- Максимум 10-15 жол

Брифинг мәтінін қайтар.
"""


class MorningBriefingService:
    """
    Morning Briefing service for daily digest.
    Generates personalized summary of:
    - Today's meetings
    - Overdue and due tasks
    - Financial summary
    - Pending invoices
    """
    
    def __init__(
        self,
        db: AsyncSession,
        api_key:Optional[ str ] = None,
        language: str = "ru"
    ):
        self.db = db
        self.api_key = api_key or settings.gemini_api_key
        self.language = language
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.model = None
    
    async def generate_briefing(
        self,
        tenant_id: UUID,
        user_name: str = "Босс"
    ) -> str:
        """Generate morning briefing for tenant."""
        data = await self._collect_data(tenant_id)
        
        if self.model:
            return await self._generate_with_ai(data, user_name)
        else:
            return self._generate_fallback(data, user_name)
    
    async def _collect_data(self, tenant_id: UUID) -> Dict[str, Any]:
        """Collect all data needed for briefing."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        yesterday_start = today_start - timedelta(days=1)
        
        # Today's meetings
        stmt = select(Meeting).where(
            and_(
                Meeting.tenant_id == tenant_id,
                Meeting.start_time >= today_start,
                Meeting.start_time < today_end,
                Meeting.status != MeetingStatus.CANCELLED.value
            )
        ).order_by(Meeting.start_time)
        result = await self.db.execute(stmt)
        meetings = result.scalars().all()
        
        # Overdue tasks
        stmt = select(Task).where(
            and_(
                Task.tenant_id == tenant_id,
                Task.deadline < now,
                Task.status != TaskStatus.DONE.value
            )
        ).order_by(Task.deadline)
        result = await self.db.execute(stmt)
        overdue_tasks = result.scalars().all()
        
        # Tasks due today
        stmt = select(Task).where(
            and_(
                Task.tenant_id == tenant_id,
                Task.deadline >= today_start,
                Task.deadline < today_end,
                Task.status != TaskStatus.DONE.value
            )
        ).order_by(Task.deadline)
        result = await self.db.execute(stmt)
        today_tasks = result.scalars().all()
        
        # Overdue invoices
        stmt = select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.status == InvoiceStatus.OVERDUE.value
            )
        )
        result = await self.db.execute(stmt)
        overdue_invoices = result.scalars().all()
        
        # Yesterday's finances
        income = 0.0
        expense = 0.0
        try:
            # Income
            stmt = select(func.sum(FinanceRecord.amount)).where(
                and_(
                    FinanceRecord.tenant_id == tenant_id,
                    FinanceRecord.type == "income",
                    FinanceRecord.record_date >= yesterday_start.date(),
                    FinanceRecord.record_date < today_start.date()
                )
            )
            result = await self.db.execute(stmt)
            income = float(result.scalar_one_or_none() or 0)
            
            # Expense
            stmt = select(func.sum(FinanceRecord.amount)).where(
                and_(
                    FinanceRecord.tenant_id == tenant_id,
                    FinanceRecord.type == "expense",
                    FinanceRecord.record_date >= yesterday_start.date(),
                    FinanceRecord.record_date < today_start.date()
                )
            )
            result = await self.db.execute(stmt)
            expense = float(result.scalar_one_or_none() or 0)
        except Exception:
            pass  # Transaction model might not exist
        
        return {
            "meetings": meetings,
            "overdue_tasks": overdue_tasks,
            "today_tasks": today_tasks,
            "overdue_invoices": overdue_invoices,
            "income": income,
            "expense": expense,
            "date": now.strftime("%d.%m.%Y, %A")
        }
    
    async def _generate_with_ai(
        self,
        data: Dict[str, Any],
        user_name: str
    ) -> str:
        """Generate briefing using AI."""
        # Format meetings
        meetings_str = "Нет встреч" if not data["meetings"] else "\n".join([
            f"- {m.start_time.strftime('%H:%M')} — {m.title}"
            for m in data["meetings"][:5]
        ])
        
        # Format overdue tasks
        overdue_str = "Нет" if not data["overdue_tasks"] else "\n".join([
            f"- {t.title} (просрочено {(datetime.now() - t.deadline).days} дн.)"
            for t in data["overdue_tasks"][:3]
        ])
        
        # Format today tasks
        today_str = "Нет" if not data["today_tasks"] else "\n".join([
            f"- {t.title}" for t in data["today_tasks"][:5]
        ])
        
        # Format invoices
        invoices_str = "Нет" if not data["overdue_invoices"] else "\n".join([
            f"- {i.debtor_name}: {i.amount:,.0f} ₸"
            for i in data["overdue_invoices"][:3]
        ])
        
        balance = data["income"] - data["expense"]
        balance_str = f"+{balance:,.0f}" if balance >= 0 else f"{balance:,.0f}"
        
        prompt_template = BRIEFING_PROMPT_KZ if self.language == "kz" else BRIEFING_PROMPT_RU
        
        prompt = prompt_template.format(
            user_name=user_name,
            date=data["date"],
            meetings=meetings_str,
            overdue_tasks=overdue_str,
            today_tasks=today_str,
            overdue_invoices=invoices_str,
            income=f"{data['income']:,.0f}",
            expense=f"{data['expense']:,.0f}",
            balance_change=balance_str
        )
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to generate briefing: {e}")
            return self._generate_fallback(data, user_name)
    
    def _generate_fallback(
        self,
        data: Dict[str, Any],
        user_name: str
    ) -> str:
        """Generate briefing without AI."""
        lines = [f"Доброе утро, {user_name}! ☕️", ""]
        
        # Meetings
        lines.append("📅 Встречи сегодня:")
        if data["meetings"]:
            for m in data["meetings"][:5]:
                lines.append(f"  {m.start_time.strftime('%H:%M')} — {m.title}")
        else:
            lines.append("  День свободен для работы!")
        lines.append("")
        
        # Overdue
        if data["overdue_tasks"]:
            lines.append("🔥 Горят дедлайны:")
            for t in data["overdue_tasks"][:3]:
                days = (datetime.now() - t.deadline).days
                lines.append(f"  • {t.title} ({days} дн. назад!)")
            lines.append("")
        
        # Today tasks
        if data["today_tasks"]:
            lines.append("✅ Задачи на сегодня:")
            for t in data["today_tasks"][:5]:
                lines.append(f"  • {t.title}")
            lines.append("")
        
        # Invoices
        if data["overdue_invoices"]:
            total = sum(float(i.amount) for i in data["overdue_invoices"])
            lines.append(f"💸 Просрочено к оплате: {total:,.0f} ₸")
            lines.append("")
        
        # Finances
        if data["income"] > 0 or data["expense"] > 0:
            balance = data["income"] - data["expense"]
            emoji = "📈" if balance >= 0 else "📉"
            lines.append(f"💰 Финансы (вчера): {emoji} {abs(balance):,.0f} ₸")
            lines.append("")
        
        lines.append("Удачного дня! 🚀")
        
        return "\n".join(lines)
    
    async def get_quick_stats(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get quick statistics for dashboard."""
        data = await self._collect_data(tenant_id)
        
        return {
            "meetings_today": len(data["meetings"]),
            "overdue_tasks": len(data["overdue_tasks"]),
            "tasks_today": len(data["today_tasks"]),
            "overdue_invoices": len(data["overdue_invoices"]),
            "overdue_amount": sum(float(i.amount) for i in data["overdue_invoices"]),
            "yesterday_income": data["income"],
            "yesterday_expense": data["expense"]
        }
