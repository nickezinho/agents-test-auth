from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.auth import DashboardDataResponse

router = APIRouter(prefix="/protected", tags=["Protected Routes"])


@router.get(
    "/dashboard",
    response_model=DashboardDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Dashboard confidencial - rota protegida por JWT"
)
async def get_dashboard_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Total de logins na trilha de auditoria
    stmt_logins = select(func.count(AuditLog.id)).where(
        AuditLog.user_id == current_user.id,
        AuditLog.event_type.in_(["LOGIN_SUCCESS_LOCAL", "LOGIN_SUCCESS_GOOGLE"])
    )
    res_logins = await db.execute(stmt_logins)
    total_logins = res_logins.scalar() or 1

    # Último IP utilizado
    stmt_last_audit = (
        select(AuditLog.ip_address)
        .where(AuditLog.user_id == current_user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    res_last_ip = await db.execute(stmt_last_audit)
    last_ip = res_last_ip.scalar() or "127.0.0.1"

    # Sessões ativas (tokens não revogados)
    stmt_sessions = select(func.count(RefreshToken.id)).where(
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked == False
    )
    res_sessions = await db.execute(stmt_sessions)
    active_sessions = res_sessions.scalar() or 1

    now = datetime.now(timezone.utc)

    return DashboardDataResponse(
        status="success",
        message="Acesso concedido à área restrita.",
        session_info={
            "user_id": str(current_user.id),
            "email": current_user.email,
            "token_issued_at": now.isoformat(),
            "token_expires_at": (now).isoformat(),
            "seconds_until_expiry": 900
        },
        metrics={
            "total_logins": total_logins,
            "last_login_ip": last_ip,
            "active_sessions_count": active_sessions
        }
    )
