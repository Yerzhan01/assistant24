import asyncio
import sys
# Add current directory to path so we can import app modules
sys.path.append('.')

from app.core.database import async_session_maker
from app.models.tenant import Tenant
from sqlalchemy import select

async def main():
    print("🔍 Searching for tenants...")
    async with async_session_maker() as db:
        result = await db.execute(select(Tenant))
        tenants = result.scalars().all()
        
        if not tenants:
            print("❌ No tenants found. Please register first.")
            return

        print(f"found {len(tenants)} tenants.")
        
        # In a real scenario, we might want to pick by email.
        # For now, we'll just pick the first one which is usually the owner/developer.
        admin_candidate = tenants[0]
        
        print(f"👤 Granting Admin rights to: {admin_candidate.email} ({admin_candidate.business_name})")
        
        admin_candidate.is_admin = True
        await db.commit()
        
        print("✅ Success! Admin rights granted.")
        print("🔄 Please refresh your browser to see the 'Админ' link in the sidebar.")

if __name__ == "__main__":
    asyncio.run(main())
