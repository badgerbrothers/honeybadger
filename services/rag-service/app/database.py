"""Database connection and session management."""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .config import settings
from .models.base import Base

# Serialize schema init across services to avoid DDL deadlocks during compose startup.
_DDL_LOCK_KEY = 734395823741  # arbitrary 64-bit integer

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
    async with engine.connect() as conn:
        # Acquire a DB-level lock so that multiple services don't run ALTER TABLE concurrently.
        await conn.execute(text("SELECT pg_advisory_lock(:key)"), {"key": _DDL_LOCK_KEY})
        try:
            # CREATE EXTENSION can fail under concurrent service startups or missing privileges.
            # Roll back explicitly so later statements can run in a clean transaction.
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await conn.commit()
            except Exception as e:
                await conn.rollback()
                logging.warning("pgvector extension not available: %s", e)

            async with conn.begin():
                await conn.run_sync(Base.metadata.create_all)
                # Keep existing databases compatible with post-microservice RAG upgrades.
                await conn.execute(
                    text(
                        """
                        ALTER TABLE document_chunk
                        ADD COLUMN IF NOT EXISTS text_search_vector TSVECTOR
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS ix_document_chunk_text_search_vector
                        ON document_chunk USING GIN (text_search_vector)
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS projects
                        ADD COLUMN IF NOT EXISTS active_rag_collection_id UUID
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS tasks
                        ADD COLUMN IF NOT EXISTS rag_collection_id UUID
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS document_chunk
                        ADD COLUMN IF NOT EXISTS rag_collection_id UUID
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS document_index_jobs
                        ADD COLUMN IF NOT EXISTS rag_collection_id UUID
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS rag_collections
                        ADD COLUMN IF NOT EXISTS owner_user_id UUID
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS document_chunk
                        ALTER COLUMN project_id DROP NOT NULL
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS document_index_jobs
                        ALTER COLUMN project_id DROP NOT NULL
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS document_index_jobs
                        ALTER COLUMN project_node_id DROP NOT NULL
                        """
                    )
                )
        finally:
            try:
                await conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": _DDL_LOCK_KEY})
                await conn.commit()
            except Exception:
                # If unlock fails due to connection state, the lock will be released on disconnect.
                pass
