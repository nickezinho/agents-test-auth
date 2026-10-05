from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status


class AppException(HTTPException):
    """Exceção base da aplicação compatível com RFC 7807 / api-contract."""

    def __init__(
        self,
        status_code: int,
        code: str,
        detail: str,
        errors: Optional[List[Dict[str, str]]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code
        self.errors = errors or []
        self.timestamp = datetime.now(timezone.utc).isoformat()


class InvalidCredentialsException(AppException):
    def __init__(self, detail: str = "E-mail ou senha inválidos."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_CREDENTIALS",
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class TokenExpiredException(AppException):
    def __init__(self, detail: str = "Token expirado. Por favor, renove sua sessão."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="TOKEN_EXPIRED",
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class InvalidTokenException(AppException):
    def __init__(self, detail: str = "Token de autenticação inválido."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_TOKEN",
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class RefreshTokenInvalidException(AppException):
    def __init__(self, detail: str = "Sessão inválida ou expirada. Efetue login novamente."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="REFRESH_TOKEN_INVALID",
            detail=detail
        )


class EmailAlreadyExistsException(AppException):
    def __init__(self, detail: str = "Já existe uma conta associada a este endereço de e-mail."):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="EMAIL_ALREADY_EXISTS",
            detail=detail
        )


class GoogleAuthFailedException(AppException):
    def __init__(self, detail: str = "Token de autenticação do Google inválido ou expirado."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="GOOGLE_AUTH_FAILED",
            detail=detail
        )
