"""Health check endpoint."""

from fastapi import APIRouter
from sqlalchemy import text
from app.database import async_session

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Basic health check with database connectivity test."""
    try:
        async with async_session() as db:
            result = await db.execute(text("SELECT 1"))
            result.scalar()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
