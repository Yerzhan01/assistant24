from __future__ import annotations
"""Contract module for tracking business agreements."""
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import t
from app.models.contract import Contract
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class ContractModule(BaseModule):
    """
    Contract module handles business agreements and ESF tracking.
    """
    
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
        user_id:Optional[ UUID ] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Process contract intent."""
        try:
            company_name = intent_data.get("company_name", "")
            contract_type = intent_data.get("contract_type", "услуги")
            
            # Parse amount
            amount = None
            if "amount" in intent_data:
                amount = Decimal(str(intent_data["amount"]))
            
            # Status
            status_map = {
                "ru": "Ожидает ЭСФ",
                "kz": "ЭСФ күтілуде"
            }
            
            # Create contract
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
            
            # Format response
            amount_str = f"{amount:,.0f}".replace(",", " ") if amount else "-"
            
            message = t(
                "modules.contract.created",
                language,
                company=company_name,
                amount=amount_str,
                status=status_map.get(language, "Pending ESF")
            )
            
            # Add ESF reminder
            esf_reminder = t("modules.contract.esf_reminder", language, company=company_name)
            message = f"{message}\n\n{esf_reminder}"
            
            return ModuleResponse(
                success=True,
                message=message,
                data={
                    "id": str(contract.id),
                    "company_name": company_name,
                    "amount": str(amount) if amount else None,
                    "status": "pending_esf"
                }
            )
            
        except Exception as e:
            return ModuleResponse(
                success=False,
                message=t("errors.invalid_data", language)
            )
    
    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
Шарттар мен келісімдерді анықтау.

Шығару керек:
- company_name: компания атауы
- amount: сома (бар болса)
- contract_type: шарт түрі (қызметтер, жеткізу, жалдау)

Мысалдар:
- "Алма ЖШС-мен 500к-ға шарт" → {"company_name": "Алма ЖШС", "amount": 500000, "contract_type": "услуги"}
- "Жаңа клиентпен келісім" → {"company_name": "Жаңа клиент", "contract_type": "услуги"}
"""
        else:
            return """
Определяй договоры и соглашения.

Извлекай:
- company_name: название компании
- amount: сумма (если указана)
- contract_type: тип договора (услуги, поставка, аренда)

Примеры:
- "Договор с ТОО Алма на 500к" → {"company_name": "ТОО Алма", "amount": 500000, "contract_type": "услуги"}
- "Подписали контракт с Kaspi" → {"company_name": "Kaspi", "contract_type": "услуги"}
- "Аренда офиса 200000 в месяц" → {"company_name": "Арендодатель", "amount": 200000, "contract_type": "аренда"}
"""
    
    def get_intent_keywords(self) -> List[str]:
        return [
            "договор", "контракт", "соглашение", "подписали", "сделка",
            "ЭСФ", "счёт-фактура", "клиент",
            "шарт", "келісім", "қол қойдық"
        ]
