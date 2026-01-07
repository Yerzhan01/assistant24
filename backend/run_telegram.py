import asyncio
import logging
import sys
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.tenant import Tenant
from app.services.telegram_bot import get_telegram_service

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("telegram_runner")

async def main():
    """Run Telegram bot in manual polling mode."""
    
    # 1. Find a tenant with a bot token
    async with async_session_maker() as db:
        stmt = select(Tenant).where(Tenant.telegram_bot_token.is_not(None))
        result = await db.execute(stmt)
        tenant = result.scalars().first()
        
        if not tenant:
            print("❌ No tenant found with a telegram_bot_token!")
            return

        tenant_id = tenant.id
        token = tenant.telegram_bot_token
        print(f"✅ Found tenant {tenant_id} with token: {token[:5]}...")

    # 2. Setup Bot & Modules
    bot = Bot(token=token)
    
    # Register modules (single source of truth)
    from app.modules.registry import registry, register_all_modules
    register_all_modules(registry)
    print(f"✅ Modules registered: {registry.get_module_ids()}")

    service = get_telegram_service()
    
    # 3. Start Autonomous Loop (proactive reminders)
    from app.agents.autonomous import start_autonomous_loop
    asyncio.create_task(start_autonomous_loop())
    print("🤖 Autonomous Loop started (reminders every hour)")
    
    # 4. Clear webhook
    print("🧹 Clearing webhook...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print(f"⚠️ Failed to delete webhook: {e}")

    print("🚀 Starting Manual Polling Loop...")
    
    offset = 0
    while True:
        try:
            # Long polling with 10s timeout
            updates = await bot.get_updates(offset=offset, timeout=10)
            
            for update in updates:
                offset = update.update_id + 1
                
                # Log update
                print(f"📥 Update {update.update_id}")
                if update.message:
                    print(f"   👤 User: {update.message.from_user.id} ({update.message.from_user.first_name})")
                    print(f"   📝 Text: {update.message.text}")
                
                # Convert to dict for the service
                update_data = update.model_dump(mode='json')
                
                try:
                    await service.process_update(tenant_id, update_data)
                except Exception as ex:
                    print(f"❌ Service Error: {ex}")
                    logger.exception("Service processing failed")
                    
        except Exception as e:
            print(f"⚠️ Polling Error: {e}")
            await asyncio.sleep(5)
        
        # Small sleep prevents strict tight loop if get_updates returns immediately
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
