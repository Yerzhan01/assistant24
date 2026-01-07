from __future__ import annotations
"""Contract module for tracking business agreements."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import t
from app.models.contract import Contract
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class ContractModule(BaseModule):
    """Contract module handles business agreements and ESF tracking."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    @property
    def info(self) -> ModuleInfo:
        return ModuleInfo(
            module_id="contract",
            name_ru="Договоры",
            name_kz="Шарттар",
            description_ru="Учёт договоров и ЭСФ",
            description_kz="Шарттар мен ЭСФ есебі",
            icon="📄"
        )
    
    async def process(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Process contract intent."""
        try:
            action = intent_data.get("action", "create").lower()
            
            handlers = {
                "list": self._list_contracts,
                "show": self._list_contracts,
                "all": self._list_contracts,
                "create": self._create_contract,
                "add": self._create_contract,
                "delete": self._delete_contract,
                "remove": self._delete_contract,
                "stats": self._get_stats,
            }
            
            handler = handlers.get(action, self._create_contract)
            return await handler(intent_data, tenant_id, user_id, language)
            
        except Exception as e:
            return ModuleResponse(success=False, message=f"Ошибка: {str(e)}")
    
    async def _list_contracts(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """List all contracts."""
        result = await self.db.execute(
            select(Contract)
            .where(Contract.tenant_id == tenant_id)
            .order_by(Contract.contract_date.desc())
            .limit(20)
        )
        contracts = result.scalars().all()
        
        if not contracts:
            if language == "kz":
                return ModuleResponse(success=True, message="📄 Шарттар тізімі бос.")
            return ModuleResponse(success=True, message="📄 Список договоров пуст.")
        
        if language == "kz":
            message = f"📄 Шарттар ({len(contracts)}):"
        else:
            message = f"📄 Договоры ({len(contracts)}):"
        
        status_icons = {"pending_esf": "⏳", "active": "✅", "completed": "✔️", "cancelled": "❌"}
        
        for c in contracts:
            icon = status_icons.get(c.status, "📄")
            amount_str = f"{c.amount:,.0f} ₸" if c.amount else ""
            date_str = c.contract_date.strftime("%d.%m.%Y") if c.contract_date else ""
            message += f"\n{icon} {c.company_name}"
            if amount_str:
                message += f" — {amount_str}"
            if date_str:
                message += f" ({date_str})"
        
        return ModuleResponse(success=True, message=message)
    
    async def _create_contract(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Create a new contract."""
        company_name = intent_data.get("company_name", "")
        
        if not company_name:
            if language == "kz":
                return ModuleResponse(success=False, message="Компания атын көрсетіңіз.")
            return ModuleResponse(success=False, message="Укажите название компании.")
        
        contract_type = intent_data.get("contract_type", "услуги")
        
        amount = None
        if "amount" in intent_data:
            amount = Decimal(str(intent_data["amount"]))
        
        contract = Contract(
            tenant_id=tenant_id,
            user_id=user_id,
            company_name=company_name,
            contract_type=contract_type,
            amount=amount,
            currency=intent_data.get("currency", "KZT"),
            status="pending_esf",
            contract_date=date.today()
        )
        
        self.db.add(contract)
        await self.db.flush()
        
        amount_str = f"{amount:,.0f} ₸" if amount else "не указана"
        
        if language == "kz":
            message = f"📄 Шарт құрылды:\n🏢 {company_name}\n💰 Сома: {amount_str}\n⏳ Күй: ЭСФ күтілуде"
        else:
            message = f"📄 Договор создан:\n🏢 {company_name}\n💰 Сумма: {amount_str}\n⏳ Статус: Ожидает ЭСФ"
        
        return ModuleResponse(success=True, message=message)
    
    async def _delete_contract(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Delete a contract."""
        company_name = intent_data.get("company_name", "")
        
        if not company_name:
            if language == "kz":
                return ModuleResponse(success=False, message="Қай шартты жою керек?")
            return ModuleResponse(success=False, message="Какой договор удалить?")
        
        result = await self.db.execute(
            select(Contract).where(
                Contract.tenant_id == tenant_id,
                Contract.company_name.ilike(f"%{company_name}%")
            ).limit(1)
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            if language == "kz":
                return ModuleResponse(success=False, message=f"'{company_name}' шарты табылмады.")
            return ModuleResponse(success=False, message=f"Договор с '{company_name}' не найден.")
        
        name = contract.company_name
        await self.db.delete(contract)
        await self.db.flush()
        
        if language == "kz":
            return ModuleResponse(success=True, message=f"🗑️ {name} шарты жойылды.")
        return ModuleResponse(success=True, message=f"🗑️ Договор с {name} удалён.")
    
    async def _get_stats(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Get contract statistics."""
        total_result = await self.db.execute(
            select(func.count(Contract.id)).where(Contract.tenant_id == tenant_id)
        )
        total = total_result.scalar_one_or_none() or 0
        
        pending_result = await self.db.execute(
            select(func.count(Contract.id)).where(
                Contract.tenant_id == tenant_id,
                Contract.status == "pending_esf"
            )
        )
        pending = pending_result.scalar_one_or_none() or 0
        
        sum_result = await self.db.execute(
            select(func.sum(Contract.amount)).where(Contract.tenant_id == tenant_id)
        )
        total_sum = sum_result.scalar_one_or_none() or 0
        
        if language == "kz":
            message = f"📄 Шарттар статистикасы:\n📋 Барлығы: {total}\n⏳ ЭСФ күтілуде: {pending}\n💰 Жалпы сома: {total_sum:,.0f} ₸"
        else:
            message = f"📄 Статистика договоров:\n📋 Всего: {total}\n⏳ Ожидают ЭСФ: {pending}\n💰 Общая сумма: {total_sum:,.0f} ₸"
        
        return ModuleResponse(success=True, message=message)
    
    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
📄 ШАРТТАР МОДУЛІ

Әрекеттер (action):
- "list" — барлық шарттарды көрсету
- "create" — жаңа шарт құру
- "delete" — шартты жою
- "stats" — статистика

Мысалдар:
- "Менің шарттарым" → {"action": "list"}
- "Шарттар тізімі" → {"action": "list"}
- "Алма ЖШС-мен 500000-ға шарт" → {"action": "create", "company_name": "Алма ЖШС", "amount": 500000}
- "Алма шартын жой" → {"action": "delete", "company_name": "Алма"}
"""
        else:
            return """
📄 МОДУЛЬ ДОГОВОРОВ

Действия (action):
- "list" — показать все договоры
- "create" — создать договор
- "delete" — удалить договор
- "stats" — статистика

Примеры запросов → JSON:
- "Мои договоры" → {"action": "list"}
- "Какие у меня договоры?" → {"action": "list"}
- "Список договоров" → {"action": "list"}
- "Договор с ТОО Алма на 500000" → {"action": "create", "company_name": "ТОО Алма", "amount": 500000}
- "Подписали контракт с Kaspi" → {"action": "create", "company_name": "Kaspi"}
- "Удали договор с Алма" → {"action": "delete", "company_name": "Алма"}
- "Сколько у меня договоров?" → {"action": "stats"}
"""
    
    def get_intent_keywords(self) -> List[str]:
        return [
            "договор", "договоры", "контракт", "соглашение", "подписали",
            "мои договоры", "список договоров", "какие договоры",
            "шарт", "шарттар", "келісім", "қол қойдық"
        ]
