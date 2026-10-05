from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.endpoints import auth, protected
from app.core.database import get_db

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(protected.router)


@api_router.get(
    "/health",
    tags=["System"],
    status_code=status.HTTP_200_OK,
    summary="Health Check de liveness e readiness"
)
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
