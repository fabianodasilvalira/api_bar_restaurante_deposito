# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Define o motor de banco de dados assíncrono
engine = create_async_engine(settings.DATABASE_URL, echo=True if settings.ENVIRONMENT == "development" else False)

# Cria uma fábrica de sessões assíncronas
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession
)

# Base para os modelos SQLAlchemy declarativos
Base = declarative_base()

# Dependência para obter uma sessão de banco de dados
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

