"""Assistant24 - AI Business Assistant API."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, modules, webhooks, settings, groups, negotiations, calendar, kz, admin, chat, finance, invoices, tasks, contacts, contracts, birthdays, ideas
from app.core.config import settings as app_settings
from app.core.database import init_db
from app.core.i18n import load_translations
from app.modules.registry import registry, register_all_modules

# Initialize Sentry
import sentry_sdk
if app_settings.sentry_dsn:
    sentry_sdk.init(
        dsn=app_settings.sentry_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events."""
    # Startup
    print("🚀 Starting Assistant24...")
    
    # Initialize database
    await init_db()
    print("✅ Database initialized")
    
    # Load translations
    load_translations()
    print("✅ Translations loaded (RU, KZ)")
    
    # Register modules (single source of truth)
    register_all_modules(registry)
    print(f"✅ Modules registered: {registry.get_module_ids()}")
    
    # Start Recurring Worker (Background Loop)
    import asyncio
    from app.workers.recurring_worker import RecurringTaskWorker
    
    async def _worker_loop():
        worker = RecurringTaskWorker()
        print("⏰ Recurring Task Worker started")
        while True:
            try:
                await worker.fast_tick()
            except Exception as e:
                logger.error(f"Worker tick failed: {e}")
            await asyncio.sleep(60)

    # fire and forget (stored in app state to prevent GC if needed, but usually fine)
    app.worker_task = asyncio.create_task(_worker_loop())
    
    yield
    
    # Shutdown
    print("👋 Shutting down Assistant24...")
    if hasattr(app, "worker_task"):
        app.worker_task.cancel()


# Create FastAPI app
app = FastAPI(
    title=app_settings.app_name,
    description="AI-помощник для бизнеса 24/7 - Assistant24",
    version="1.0.0",
    lifespan=lifespan
)

# Global Exception Handler
import logging
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("api")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global handler to catch all unhandled exceptions."""
    logger.error(f"Global Exception: {exc}")
    traceback.print_exc()  # Print to console for dev visibility
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "error_type": type(exc).__name__,
            "message": str(exc),
            # In production, we might want to hide the traceback or message
        },
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://link-it.tech",
        "https://www.link-it.tech",
        "https://dev.link-it.tech",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(modules.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api/v1")
app.include_router(groups.router)  # Already has /api/v1 prefix
app.include_router(negotiations.router)  # Already has /api/v1 prefix
app.include_router(calendar.router)  # Already has /api/v1 prefix
app.include_router(kz.router)  # Kazakhstan localization (currency, holidays)
app.include_router(admin.router)  # Admin panel APIs
app.include_router(chat.router)  # AI Chat API
app.include_router(finance.router)
app.include_router(invoices.router)
app.include_router(tasks.router)
app.include_router(contacts.router)
app.include_router(contracts.router)
app.include_router(birthdays.router)
app.include_router(ideas.router)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "name": app_settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "modules": registry.get_module_ids()
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
