import asyncio
import sys
sys.path.insert(0, '/app')

from app.core.database import async_session_maker
from app.services.ai_router import AIRouter
from app.modules.registry import get_registry, register_all_modules
from uuid import UUID

TENANT_ID = UUID("0c1ab996-7d02-4dba-9a6b-a8f8a5d84a91")
USER_ID = UUID("b1b43fd1-d8ce-4df5-9d75-6d408612e066")

# Тест модулей - по 3 запроса на каждый
TEST_CASES = {
    "assistant": [
        "Привет",
        "Как дела?",
        "Кто ты?",
    ],
    "task": [
        "Мои задачи",
        "Покажи задачи",
        "Создай задачу позвонить маме",
    ],
    "contacts": [
        "Мои контакты",
        "Покажи контакты", 
        "Найди контакт Ажар",
    ],
    "finance": [
        "Мой баланс",
        "Какой у меня баланс?",
        "Покажи расходы",
    ],
    "meeting": [
        "Мои встречи",
        "Встречи на сегодня",
    ],
    "birthday": [
        "Дни рождения",
        "Покажи дни рождения",
    ],
    "ideas": [
        "Мои идеи",
        "Покажи идеи",
    ],
    "debtor": [
        "Мои должники",
        "Кто мне должен?",
    ],
    "contract": [
        "Мои договоры",
        "Покажи договоры",
    ],
    "report": [
        "Отчет за день",
        "Дай сводку",
    ],
}

async def main():
    print("🧪 ПОЛНЫЙ ТЕСТ ВСЕХ МОДУЛЕЙ")
    print("=" * 70)
    
    # Register modules
    registry = get_registry()
    register_all_modules(registry)
    all_modules = list(registry._modules.values())
    print(f"📦 Loaded {len(all_modules)} modules")
    
    results = {"passed": 0, "failed": 0}
    
    async with async_session_maker() as db:
        for module_name, messages in TEST_CASES.items():
            print(f"\n{'='*70}")
            print(f"📦 MODULE: {module_name.upper()}")
            print("=" * 70)
            
            for msg in messages:
                try:
                    router = AIRouter(db, language="ru")
                    result = await router.process_message(
                        message=msg,
                        tenant_id=TENANT_ID,
                        user_id=USER_ID,
                        enabled_modules=all_modules
                    )
                    
                    response = result.message[:150] if result.message else "NO RESPONSE"
                    status = "✅" if result.success else "❌"
                    print(f"\n{status} INPUT:  {msg}")
                    print(f"   OUTPUT: {response}")
                    
                    if result.success:
                        results["passed"] += 1
                    else:
                        results["failed"] += 1
                        
                except Exception as e:
                    print(f"\n❌ INPUT:  {msg}")
                    print(f"   ERROR:  {str(e)[:100]}")
                    results["failed"] += 1
                
                await asyncio.sleep(0.5)
    
    print(f"\n\n{'='*70}")
    print(f"📊 ИТОГО: {results['passed']} passed, {results['failed']} failed")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
