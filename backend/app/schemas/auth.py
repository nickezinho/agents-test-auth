from typing import Any, Dict, Optional
from pydantic import BaseModel, EmailStr, Field
from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(..., min_length=10)


class AuthSuccessResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 900
    user: UserResponse


class LogoutResponse(BaseModel):
    message: str = "Sessão encerrada com sucesso."


class DashboardDataResponse(BaseModel):
    status: str = "success"
    message: str = "Acesso concedido à área restrita."
    session_info: Dict[str, Any]
    metrics: Dict[str, Any]
