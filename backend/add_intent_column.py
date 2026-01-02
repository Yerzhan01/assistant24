import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Database URL
DATABASE_URL = "sqlite+aiosqlite:///./digital_secretary.db"

async def add_intent_column():
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        try:
            print("Checking if 'intent' column exists in 'messages' table...")
            # Try to select the column to see if it exists
            await conn.execute(text("SELECT intent FROM messages LIMIT 1"))
            print("Column 'intent' already exists.")
        except Exception:
            print("Column 'intent' does not exist. Adding it...")
            # If it fails, add the column
            await conn.execute(text("ALTER TABLE messages ADD COLUMN intent VARCHAR"))
            print("Successfully added 'intent' column.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_intent_column())
