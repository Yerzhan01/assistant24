
import asyncio
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.finance import FinanceRecord
from app.models.meeting import Meeting
from app.models.chat import Message
from app.models.tenant import Tenant

async def dump_data():
    async with async_session_maker() as session:
        print("--- TENANTS ---")
        stmt = select(Tenant)
        tenants = (await session.execute(stmt)).scalars().all()
        for t in tenants:
            print(f"Tenant: {t.id} ({t.email})")
            
            print(f"  --- FINANCE ({t.email}) ---")
            f_stmt = select(FinanceRecord).where(FinanceRecord.tenant_id == t.id)
            recs = (await session.execute(f_stmt)).scalars().all()
            for r in recs:
                print(f"    {r.record_date} {r.type} {r.amount} - {r.category} (Desc: {r.description})")
                
            print(f"  --- MEETINGS ({t.email}) ---")
            m_stmt = select(Meeting).where(Meeting.tenant_id == t.id)
            meets = (await session.execute(m_stmt)).scalars().all()
            for m in meets:
                print(f"    {m.start_time} - {m.title} (Status: {m.status})")

            print(f"  --- CHAT ({t.email}) ---")
            c_stmt = select(Message).where(Message.tenant_id == t.id).order_by(Message.created_at.desc()).limit(5)
            msgs = (await session.execute(c_stmt)).scalars().all()
            for msg in msgs:
                print(f"    [{msg.created_at}] {msg.role}: {msg.content[:50]}...")

if __name__ == "__main__":
    asyncio.run(dump_data())
