from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.deps import get_current_tenant, get_db
from app.models.finance import FinanceRecord
from app.models.tenant import Tenant

router = APIRouter(prefix="/api/v1/finance", tags=["finance"])

class TransactionResponse(BaseModel):
    id: str
    amount: float
    category: str
    description: Optional[str]
    date: datetime
    type: str  # "income" or "expense"

class TransactionCreate(BaseModel):
    amount: float
    category: str
    description: Optional[str] = None
    date: str  # Frontend sends YYYY-MM-DD string
    type: str
    contact_name: Optional[str] = None

@router.post("/transactions", response_model=TransactionResponse)
async def create_transaction(
    tx: TransactionCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    try:
        record_date_obj = datetime.strptime(tx.date, "%Y-%m-%d").date()
    except ValueError:
        try:
             record_date_obj = datetime.fromisoformat(tx.date).date()
        except:
             record_date_obj = datetime.now().date()

    record = FinanceRecord(
        tenant_id=tenant.id,
        user_id=None,
        type=tx.type,
        amount=tx.amount,
        category=tx.category,
        description=tx.description or tx.contact_name,
        record_date=record_date_obj
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    
    return TransactionResponse(
        id=str(record.id),
        amount=float(record.amount),
        category=record.category,
        description=record.description,
        date=datetime.combine(record.record_date, datetime.min.time()),
        type=record.type
    )

@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(FinanceRecord).where(FinanceRecord.tenant_id == tenant.id)
    if start_date:
        stmt = stmt.where(FinanceRecord.record_date >= start_date)
    if end_date:
        stmt = stmt.where(FinanceRecord.record_date <= end_date)
    
    stmt = stmt.order_by(FinanceRecord.record_date.desc()).limit(limit)
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    return [
        TransactionResponse(
            id=str(r.id),
            amount=r.amount,
            category=r.category,
            description=r.description,
            date=r.record_date,
            type=r.type
        ) for r in records
    ]

@router.get("/summary")
async def get_summary(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    # Fetch all records for the tenant (simple aggregation in python for reliability)
    stmt = select(FinanceRecord).where(FinanceRecord.tenant_id == tenant.id)
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    total_income = 0.0
    total_expense = 0.0
    this_month_income = 0.0
    this_month_expense = 0.0
    
    now = datetime.now()
    month_start = now.date().replace(day=1) # Use date() for comparison with record_date (Date)
    
    for r in records:
        val = float(r.amount) if r.amount else 0.0
        if r.type == "income":
            total_income += val
            if r.record_date >= month_start:
                this_month_income += val
        elif r.type == "expense":
            total_expense += val
            if r.record_date >= month_start:
                this_month_expense += val
    
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": total_income - total_expense,
        "this_month_income": this_month_income,
        "this_month_expense": this_month_expense
    }

@router.get("/reports")
async def get_reports(
    period: str = "month",
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Generate finance reports."""
    # 1. Fetch all records
    stmt = select(FinanceRecord).where(
        FinanceRecord.tenant_id == tenant.id
    ).order_by(FinanceRecord.record_date)
    
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    # 2. Aggregate Monthly Data
    monthly_map = {}
    total_income = 0.0
    total_expense = 0.0
    
    income_cats = {}
    expense_cats = {}
    
    for r in records:
        # Month key: "Jan", "Feb" etc. Or "YYYY-MM"
        # Frontend seems to handle strings nicely. Let's use short month names or YYYY-MM
        # Frontend demo data used 'Янв', 'Фев'. 
        m_key = r.record_date.strftime("%b") # Jan, Feb... (English unfortunately without locale reqs)
        # Better: use YYYY-MM and let frontend format? Frontend just displays.
        # Let's use numeric month for sorting?
        # Replicating frontend demo style:
        month_names = ["", "Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
        m_idx = r.record_date.month
        m_name = month_names[m_idx] if 1 <= m_idx <= 12 else str(m_idx)
        
        val = float(r.amount) if r.amount else 0.0
        
        if m_name not in monthly_map:
            monthly_map[m_name] = {"month": m_name, "income": 0.0, "expense": 0.0}
            
        if r.type == "income":
            monthly_map[m_name]["income"] += val
            total_income += val
            income_cats[r.category] = income_cats.get(r.category, 0.0) + val
        else:
            monthly_map[m_name]["expense"] += val
            total_expense += val
            expense_cats[r.category] = expense_cats.get(r.category, 0.0) + val
            
    # Convert map to list
    monthly_data = list(monthly_map.values())
    
    # 3. Categories
    def format_cats(cat_map, total):
        res = []
        colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16']
        idx = 0
        sorted_cats = sorted(cat_map.items(), key=lambda x: x[1], reverse=True)
        for cat, val in sorted_cats:
            res.append({
                "category": cat,
                "amount": val,
                "percentage": round((val / total * 100), 1) if total > 0 else 0,
                "color": colors[idx % len(colors)]
            })
            idx += 1
        return res

    inc_cats_list = format_cats(income_cats, total_income)
    exp_cats_list = format_cats(expense_cats, total_expense)
    
    top_inc = inc_cats_list[0]["category"] if inc_cats_list else "-"
    top_exp = exp_cats_list[0]["category"] if exp_cats_list else "-"
    
    return {
        "monthly": monthly_data,
        "income_categories": inc_cats_list,
        "expense_categories": exp_cats_list,
        "summary": {
            "total_income": total_income,
            "total_expense": total_expense,
            "profit": total_income - total_expense,
            "profit_margin": round(((total_income - total_expense) / total_income * 100), 1) if total_income > 0 else 0,
            "top_income_category": top_inc,
            "top_expense_category": top_exp
        }
    }
