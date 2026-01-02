import asyncio
import sys
import urllib.request
from sqlalchemy import text
# Add current directory to path
sys.path.append('.')
from app.core.database import async_session_maker

async def check_db():
    print("🔍 Checking Database...")
    try:
        async with async_session_maker() as db:
            # Simple query
            await db.execute(text("SELECT 1"))
            print("✅ Database connection successful.")
            return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def check_api():
    print("🔍 Checking Backend API...")
    try:
        url = "http://localhost:8000/docs"
        status = urllib.request.urlopen(url).getcode()
        if status == 200:
             print("✅ Backend API is reachable (200 OK).")
             return True
        else:
             print(f"⚠️ Backend API returned status {status}")
             return False
    except Exception as e:
        print(f"❌ Backend API unreachable: {e}")
        return False

async def main():
    db_ok = await check_db()
    api_ok = check_api()
    
    if db_ok and api_ok:
        print("\n🚀 SYSTEM STATUS: FUNCTIONAL")
    else:
        print("\n⚠️ SYSTEM STATUS: ISSUES DETECTED")

if __name__ == "__main__":
    asyncio.run(main())
