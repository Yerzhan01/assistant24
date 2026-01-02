import asyncio
import os
import sys

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
from app.core.database import async_session_maker
from app.models.trace import Trace

# Import all models to ensure partial relationship resolution works
# or at least enough to satisfy Tenant mapper
from app.models.tenant import Tenant
from app.models.user import User
from app.models.idea import Idea
from app.models.contact import Contact
from app.models.task import Task
from app.models.meeting import Meeting
from app.models.finance import FinanceRecord
from app.models.whatsapp_instance import WhatsAppInstance
from app.models.group_chat import GroupChat
from app.models.birthday import Birthday

async def fix_analytics():
    print("Starting analytics backfill...")
    async with async_session_maker() as db:
        # Check for traces with null model
        stmt = select(Trace).where(Trace.gemini_model.is_(None))
        result = await db.execute(stmt)
        traces = result.scalars().all()
        
        print(f"Found {len(traces)} traces with missing analytics data.")
        
        if not traces:
            print("No fix needed.")
            return

        # Update them
        # We set token counts to 0 so they don't skew cost wildly, 
        # but setting the model allows them to appear in charts.
        stmt = update(Trace).where(
            Trace.gemini_model.is_(None)
        ).values(
            gemini_model="gemini-1.5-flash", # Use a standard name that triggers pricing
            gemini_prompt_tokens=0,
            gemini_response_tokens=0
        )
        
        await db.execute(stmt)
        await db.commit()
        print("Successfully updated traces.")

if __name__ == "__main__":
    asyncio.run(fix_analytics())
