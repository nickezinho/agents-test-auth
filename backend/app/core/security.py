import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Hash Argon2id sintaticamente válido pré-computado para mitigação de timing attack
DUMMY_ARGON2_HASH = "$argon2id$v=19$m=65536,t=3,p=4$ZHVtbXlzYWx0MTIzNDU2Nw$4hW6/o5h2Zt2T1d7u4d1wY0kUqX+1m9o0v4Gz/Y9r1s"


def get_password_hash(password: str) -> str:
    """Gera hash Argon2id seguro a partir da senha em texto plano."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compara senha em tempo constante contra o hash Argon2id."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    """Cria JWT de acesso com validade curta (15 minutos)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "token_type": "access"
    }
    if extra_claims:
        payload.update(extra_claims)

    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodifica e valida assinatura e expiração do JWT de acesso."""
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "sub", "jti"]}
    )
    if payload.get("token_type") != "access":
        raise jwt.InvalidTokenError("Tipo de token inválido para esta operação.")
    return payload


def generate_refresh_token() -> str:
    """Gera um token criptográfico aleatório e opaco com 64 bytes de entropia."""
    return secrets.token_urlsafe(64)


def hash_token(token: str) -> str:
    """Gera o hash SHA-256 do token opaco para armazenamento seguro no banco."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
