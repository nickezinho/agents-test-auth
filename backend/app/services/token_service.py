import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import RefreshTokenInvalidException
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_token,
)
from app.models.audit import AuditLog
from app.models.token import RefreshToken
from app.models.user import User


class TokenService:

    @staticmethod
    async def create_session_tokens(
        db: AsyncSession,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        family_id: Optional[uuid.UUID] = None
    ) -> Tuple[str, str]:
        """Cria um novo par de Access Token (JWT) e Refresh Token (rotativo) persistido."""
        # Se não informada, cria uma nova família de tokens
        active_family_id = family_id or uuid.uuid4()
        raw_refresh_token = generate_refresh_token()
        token_hashed = hash_token(raw_refresh_token)

        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        new_refresh = RefreshToken(
            user_id=user.id,
            token_hash=token_hashed,
            family_id=active_family_id,
            revoked=False,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(new_refresh)

        # Log de auditoria
        audit = AuditLog(
            user_id=user.id,
            event_type="SESSION_CREATED",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_info={"family_id": str(active_family_id)}
        )
        db.add(audit)
        await db.commit()

        # Cria Access Token JWT
        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email, "name": user.full_name}
        )

        return access_token, raw_refresh_token

    @staticmethod
    async def rotate_refresh_token(
        db: AsyncSession,
        raw_refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[str, str]:
        """Executa rotação atômica com detecção de reuso (RFC 6749 / OAuth 2.0 BCP)."""
        if not raw_refresh_token:
            raise RefreshTokenInvalidException("Refresh token não informado.")

        token_hashed = hash_token(raw_refresh_token)

        # Consulta o token pelo hash
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hashed)
        result = await db.execute(stmt)
        token_record = result.scalars().first()

        if not token_record:
            raise RefreshTokenInvalidException("Sessão inexistente ou token inválido.")

        # Detecção de Reuso: se o token já foi revogado/usado
        if token_record.revoked:
            # ATAQUE DE REUSO DETECTADO! Revoga toda a família de tokens do usuário
            stmt_revoke_family = (
                update(RefreshToken)
                .where(RefreshToken.family_id == token_record.family_id)
                .values(revoked=True)
            )
            await db.execute(stmt_revoke_family)

            # Registro de auditoria de incidente
            audit_incident = AuditLog(
                user_id=token_record.user_id,
                event_type="TOKEN_REUSE_DETECTED",
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_info={
                    "family_id": str(token_record.family_id),
                    "token_id": str(token_record.id),
                    "severity": "CRITICAL"
                }
            )
            db.add(audit_incident)
            await db.commit()

            raise RefreshTokenInvalidException(
                "Alerta de segurança: violação de integridade de sessão detectada. Todos os tokens foram revogados."
            )

        # Checagem de expiração temporal
        now = datetime.now(timezone.utc)
        token_exp = token_record.expires_at
        if token_exp.tzinfo is None:
            token_exp = token_exp.replace(tzinfo=timezone.utc)

        if token_exp < now:
            token_record.revoked = True
            await db.commit()
            raise RefreshTokenInvalidException("Refresh token expirado. Faça login novamente.")

        # Marca o token atual como consumido
        token_record.revoked = True
        token_record.used_at = now

        # Busca o usuário associado
        user_stmt = select(User).where(User.id == token_record.user_id)
        user_res = await db.execute(user_stmt)
        user = user_res.scalars().first()
        if not user or not user.is_active:
            await db.commit()
            raise RefreshTokenInvalidException("Usuário inativo ou inexistente.")

        # Emite novo par de tokens sob a mesma family_id
        new_raw_refresh = generate_refresh_token()
        new_token_hashed = hash_token(new_raw_refresh)
        new_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        new_refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=new_token_hashed,
            family_id=token_record.family_id,
            revoked=False,
            expires_at=new_expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(new_refresh_record)
        await db.commit()

        new_access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email, "name": user.full_name}
        )

        return new_access_token, new_raw_refresh

    @staticmethod
    async def revoke_refresh_token(db: AsyncSession, raw_refresh_token: str) -> bool:
        """Revoga o token no logout."""
        if not raw_refresh_token:
            return False

        token_hashed = hash_token(raw_refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hashed)
        result = await db.execute(stmt)
        token_record = result.scalars().first()

        if token_record:
            token_record.revoked = True
            await db.commit()
            return True
        return False
