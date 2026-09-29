import sys
import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.api.chat import router as chat_router
from app.api.orders import router as orders_router
from app.api.tickets import router as tickets_router
from app.api.health import router as health_router
from app.observability.logging import setup_logging

# Initialize logging
setup_logging()

app = FastAPI(
    title="Restaurant Support & Operations Agent",
    description="AI-powered customer support agent for restaurant delivery platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Include API routers
app.include_router(chat_router)
app.include_router(orders_router)
app.include_router(tickets_router)
app.include_router(health_router)

# Serve static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """Serve the chat interface."""
    html_path = static_dir / "chat.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return {"message": "Restaurant Support Agent API", "docs": "/docs"}


@app.get("/api", include_in_schema=False)
async def api_info():
    """API information."""
    return {
        "name": "Restaurant Support & Operations Agent",
        "version": "1.0.0",
        "endpoints": {
            "chat": "POST /api/agent/chat",
            "orders": "GET /api/orders/{order_code}",
            "order_status": "GET /api/orders/{order_code}/status",
            "tickets": "POST /api/support/tickets",
            "health": "GET /health",
            "docs": "GET /docs",
        },
    }
