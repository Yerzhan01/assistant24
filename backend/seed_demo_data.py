
import asyncio
import uuid
from datetime import datetime, timedelta
import random

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

# Import models
# We need to set the python path or run this from the backend dir
import sys
import os
sys.path.append(os.getcwd())

from app.core.config import settings
from app.models.tenant import Tenant
from app.models.user import User
from app.models.meeting import Meeting, MeetingStatus, MeetingPriority
from app.models.contact import Contact
from app.models.finance import FinanceRecord
from app.core.security import get_password_hash
from app.core.database import Base
from sqlalchemy import JSON

# Setup DB
DATABASE_URL = "sqlite+aiosqlite:///./digital_secretary.db"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def seed_data():
    async with AsyncSessionLocal() as session:
        print("🌱 Seeding demo data...")
        
        # 1. Create Tenant (Business)
        # Check if exists first
        result = await session.execute(select(Tenant).where(Tenant.email == "demo@digital-secretary.kz"))
        existing = result.scalar_one_or_none()
        
        if existing:
            print("✅ Demo tenant already exists.")
            return

        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id,
            email="demo@digital-secretary.kz",
            hashed_password=get_password_hash("demo123"),
            business_name="ТОО 'Kazakhstan Innovations'",
            plan="pro",
            language="ru",
            timezone="Asia/Almaty",
            ai_enabled=True
        )
        session.add(tenant)
        
        # 2. Create User (Boss)
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            name="Бақыт",
            role="owner",
            is_active=True,
            language="ru"
        )
        session.add(user)
        
        # 3. Create Contacts
        contacts = []
        names = ["Асхат (Бухгалтер)", "Алия (Маркетинг)", "Директор (Партнер)", "Ержан (IT)"]
        for name in names:
            contact = Contact(
                tenant_id=tenant_id,
                name=name,
                phone=f"777{random.randint(10000000, 99999999)}",
                tags=["work"]
            )
            session.add(contact)
            contacts.append(contact)
            
        await session.flush() # to get IDs
        
        # 4. Create Meetings (Past and Future)
        
        # Future meeting tomorrow
        tomorrow_10am = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
        meeting1 = Meeting(
            tenant_id=tenant_id,
            user_id=user_id,
            title="Встреча с партнерами по запуску",
            description="Обсудить стратегию выхода на рынок Алматы.",
            start_time=tomorrow_10am,
            end_time=tomorrow_10am + timedelta(hours=1),
            location="Офис, переговорная 1",
            priority=MeetingPriority.HIGH.value,
            status=MeetingStatus.CONFIRMED.value,
            color="#EF4444" # Red
        )
        session.add(meeting1)
        
        # Past meeting
        yesterday_2pm = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0) - timedelta(days=1)
        meeting2 = Meeting(
            tenant_id=tenant_id,
            user_id=user_id,
            title="Еженедельная летучка",
            description="Отчет по KPI за неделю.",
            start_time=yesterday_2pm,
            end_time=yesterday_2pm + timedelta(minutes=30),
            location="Zoom",
            status=MeetingStatus.COMPLETED.value,
            color="#3B82F6" # Blue
        )
        session.add(meeting2)

        # 5. Create Finance Data for Reports
        
        # Income Record
        income = FinanceRecord(
            tenant_id=tenant_id,
            user_id=user_id,
            type="income",
            amount=500000.0,
            currency="KZT",
            category="sales",
            description="Оплата по договору №123",
            record_date=datetime.now().date() - timedelta(days=2)
        )
        session.add(income)
        
        # Expense Record
        expense = FinanceRecord(
            tenant_id=tenant_id,
            user_id=user_id,
            type="expense",
            amount=150000.0,
            currency="KZT",
            category="office",
            description="Аренда офиса",
            record_date=datetime.now().date() - timedelta(days=5)
        )
        session.add(expense)

        await session.commit()
        print("✨ Magic Onboarding Complete! User created.")
        print("📧 Email: demo@digital-secretary.kz")
        print("🔑 Pass: demo123")

if __name__ == "__main__":
    asyncio.run(seed_data())
