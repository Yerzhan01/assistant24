import asyncio
from app.core.database import async_session_maker
from app.models.tenant import Tenant
from sqlalchemy import select

async def main():
    async with async_session_maker() as db:
        stmt = select(Tenant)
        result = await db.execute(stmt)
        tenants = result.scalars().all()
        
        print(f"Total tenants: {len(tenants)}")
        for t in tenants:
             print(f"Tenant: {t.id} - Name: {t.name} - Token: {t.telegram_bot_token}")

if __name__ == "__main__":
    asyncio.run(main())
