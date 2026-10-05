from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import (
    EmailAlreadyExistsException,
    InvalidCredentialsException,
)
from app.core.security import DUMMY_ARGON2_HASH, get_password_hash, verify_password
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.schemas.user import UserCreate


class AuthService:

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower().strip())
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: Any) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def register_user(
        db: AsyncSession,
        user_in: UserCreate,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> User:
        # Normaliza e-mail
        normalized_email = user_in.email.lower().strip()
        existing = await AuthService.get_by_email(db, normalized_email)
        if existing:
            raise EmailAlreadyExistsException()

        # Hash Argon2id da senha
        hashed_pw = get_password_hash(user_in.password)

        new_user = User(
            email=normalized_email,
            hashed_password=hashed_pw,
            full_name=user_in.full_name.strip(),
            is_active=True,
            is_oauth_only=False
        )
        db.add(new_user)

        # Log de auditoria
        audit = AuditLog(
            user_id=new_user.id,
            event_type="USER_REGISTERED",
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    @staticmethod
    async def authenticate_local(
        db: AsyncSession,
        login_data: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> User:
        normalized_email = login_data.email.lower().strip()
        user = await AuthService.get_by_email(db, normalized_email)

        # Proteção contra timing attack caso o usuário não exista ou seja OAuth-only
        if not user or not user.hashed_password:
            # Executa dummy verification para manter tempo de resposta constante
            try:
                verify_password("dummy_password_for_timing_protection", DUMMY_ARGON2_HASH)
            except Exception:
                pass
            audit = AuditLog(
                user_id=None,
                event_type="LOGIN_FAILED_NOT_FOUND",
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_info={"attempted_email": normalized_email}
            )
            db.add(audit)
            await db.commit()
            raise InvalidCredentialsException()

        if not verify_password(login_data.password, user.hashed_password):
            audit = AuditLog(
                user_id=user.id,
                event_type="LOGIN_FAILED_WRONG_PASSWORD",
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.add(audit)
            await db.commit()
            raise InvalidCredentialsException()

        if not user.is_active:
            raise InvalidCredentialsException("Esta conta está desativada.")

        # Log de login bem-sucedido
        audit = AuditLog(
            user_id=user.id,
            event_type="LOGIN_SUCCESS_LOCAL",
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit)
        await db.commit()
        return user

    @staticmethod
    async def authenticate_or_register_google(
        db: AsyncSession,
        google_info: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> User:
        google_sub = google_info.get("sub")
        email = google_info.get("email", "").lower().strip()
        name = google_info.get("name") or email.split("@")[0]
        picture = google_info.get("picture")

        # Busca por google_sub primeiro
        stmt = select(User).where(User.google_sub == google_sub)
        res = await db.execute(stmt)
        user = res.scalars().first()

        if not user:
            # Busca por email para fazer vinculação de contas (account linking)
            user = await AuthService.get_by_email(db, email)
            if user:
                user.google_sub = google_sub
                if picture and not user.avatar_url:
                    user.avatar_url = picture
            else:
                # Cria novo usuário OAuth-only
                user = User(
                    email=email,
                    hashed_password=None,
                    full_name=name,
                    avatar_url=picture,
                    google_sub=google_sub,
                    is_active=True,
                    is_oauth_only=True
                )
                db.add(user)

        if not user.is_active:
            raise InvalidCredentialsException("Conta desativada.")

        audit = AuditLog(
            user_id=user.id,
            event_type="LOGIN_SUCCESS_GOOGLE",
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit)
        await db.commit()
        await db.refresh(user)
        return user
