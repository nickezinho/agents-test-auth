import uuid
from typing import Optional
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import (
    InvalidTokenException,
    TokenExpiredException,
)
from app.core.security import decode_access_token
from app.models.user import User
from app.services.auth_service import AuthService

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extrai e valida o Access Token JWT do cabeçalho Authorization: Bearer."""
    if not credentials or not credentials.credentials:
        raise InvalidTokenException("Token de autorização não fornecido.")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise TokenExpiredException()
    except jwt.InvalidTokenError as e:
        raise InvalidTokenException(f"Token inválido: {str(e)}")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise InvalidTokenException("Identificador de usuário ausente no token.")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise InvalidTokenException("Identificador de usuário inválido.")

    user = await AuthService.get_by_id(db, user_uuid)
    if not user:
        raise InvalidTokenException("Usuário não encontrado.")

    if not user.is_active:
        raise InvalidTokenException("Usuário inativo.")

    return user


def get_client_ip(request: Request) -> str:
    """Obtém o IP real do cliente, considerando proxies reversos como Nginx."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    return request.headers.get("User-Agent", "unknown")
