from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Engine assíncrono
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG and settings.ENVIRONMENT == "development",
    future=True,
    # Argumentos específicos para sqlite vs postgresql
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# Fabrica de sessões assíncronas
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)


class Base(DeclarativeBase):
    """Base declarativa com convenções padrão."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Injetor de dependência FastAPI para sessões do SQLAlchemy."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
