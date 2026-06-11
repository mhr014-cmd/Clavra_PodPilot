from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.core.constants import APP_NAME, APP_VERSION

# ── Route imports ─────────────────────────────────────────────────────────
from app.routes.auth_routes        import router as auth_router
from app.routes.orders             import router as orders_router
from app.routes.inventory          import router as inventory_router
from app.routes.shipment           import router as shipment_router
from app.routes.production_lines   import router as production_lines_router
from app.routes.production         import router as production_router
from app.routes.analytics          import router as analytics_router
from app.routes.inventory_analytics import router as inv_analytics_router
from app.routes.ai_chat            import router as ai_chat_router
from app.routes.notification       import router as notification_router
from app.routes.knowledge_routes   import router as knowledge_router
from app.routes.quality_routes     import router as quality_router

# ── App factory ───────────────────────────────────────────────────────────
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Manufacturing AI Operating System — by Clavra",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static uploads folder ─────────────────────────────────────────────────
uploads_dir = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
os.makedirs(uploads_dir, exist_ok=True)
try:
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
except Exception:
    pass  # Skip if directory empty on first run

# ── Health check ──────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def health():
    return {
        "status": "running",
        "app": APP_NAME,
        "version": APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}

@app.get("/debug-cors", tags=["Health"])
def debug_cors():
    return {"allowed_origins": settings.get_allowed_origins(), "raw": settings.ALLOWED_ORIGINS}

# ── Routers ───────────────────────────────────────────────────────────────
app.include_router(auth_router)                                           # /auth/...
app.include_router(orders_router,           prefix="/orders",            tags=["Orders"])
app.include_router(inventory_router,        prefix="/inventory",         tags=["Inventory"])
app.include_router(shipment_router,         prefix="/shipments",         tags=["Shipments"])
app.include_router(production_lines_router, prefix="/production-lines",  tags=["Production Lines"])
app.include_router(production_router,       prefix="/production",        tags=["Production"])
app.include_router(analytics_router)                                      # /analytics/...
app.include_router(inv_analytics_router)                                  # /analytics/inventory
app.include_router(ai_chat_router)                                        # /ai/...
app.include_router(notification_router,     prefix="/notifications",     tags=["Notifications"])
app.include_router(knowledge_router)                                      # /knowledge/...
app.include_router(quality_router)                                        # /quality/...
