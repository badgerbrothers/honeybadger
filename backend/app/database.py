"""Database connection and session management."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .config import settings
from .models.base import Base

# Create async engine
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_pre_ping=True,
)

# Create async session maker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    """Dependency for FastAPI to get database session."""
    async with async_session_maker() as session:
        yield session

async def init_db():
    """Initialize database tables (for development only)."""
    async with engine.begin() as conn:
        # Try to enable pgvector extension (skip if not installed)
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as e:
            # pgvector not installed - log warning and continue
            import logging
            logging.warning(f"pgvector extension not available: {e}")
        await conn.run_sync(Base.metadata.create_all)
