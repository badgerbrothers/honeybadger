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
                        ALTER TABLE IF EXISTS tasks
                        ADD COLUMN IF NOT EXISTS queue_status queuestatus
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS tasks
                        ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMP WITHOUT TIME ZONE
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS tasks
                        ADD COLUMN IF NOT EXISTS priority INTEGER
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS tasks
                        ADD COLUMN IF NOT EXISTS assigned_agent VARCHAR(100)
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        UPDATE tasks
                        SET queue_status = 'SCHEDULED'
                        WHERE queue_status IS NULL
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        UPDATE tasks
                        SET priority = 0
                        WHERE priority IS NULL
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS tasks
                        ALTER COLUMN queue_status SET DEFAULT 'SCHEDULED'
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS tasks
                        ALTER COLUMN queue_status SET NOT NULL
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS tasks
                        ALTER COLUMN priority SET DEFAULT 0
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS tasks
                        ALTER COLUMN priority SET NOT NULL
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS ix_tasks_queue_status ON tasks (queue_status)
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS ix_tasks_scheduled_at ON tasks (scheduled_at)
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS ix_tasks_priority ON tasks (priority)
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
                        ALTER TABLE IF EXISTS project_nodes
                        ALTER COLUMN size TYPE BIGINT
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
                        ALTER TABLE IF EXISTS document_index_jobs
                        ADD COLUMN IF NOT EXISTS error_code VARCHAR(100)
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS document_index_jobs
                        ADD COLUMN IF NOT EXISTS failed_step VARCHAR(100)
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
                        ALTER TABLE IF EXISTS sandbox_sessions
                        ALTER COLUMN task_run_id DROP NOT NULL
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS sandbox_sessions
                        ADD COLUMN IF NOT EXISTS status VARCHAR(50)
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS sandbox_sessions
                        ADD COLUMN IF NOT EXISTS workspace_dir VARCHAR(512)
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS sandbox_sessions
                        ADD COLUMN IF NOT EXISTS reuse_count INTEGER
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS sandbox_sessions
                        ADD COLUMN IF NOT EXISTS leased_at TIMESTAMP WITHOUT TIME ZONE
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS sandbox_sessions
                        ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMP WITHOUT TIME ZONE
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS sandbox_sessions
                        ADD COLUMN IF NOT EXISTS last_health_check_at TIMESTAMP WITHOUT TIME ZONE
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS sandbox_sessions
                        ADD COLUMN IF NOT EXISTS lease_error VARCHAR(255)
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS sandbox_sessions
                        ADD COLUMN IF NOT EXISTS drain_reason VARCHAR(255)
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        UPDATE sandbox_sessions
                        SET status = CASE
                            WHEN terminated_at IS NOT NULL THEN 'broken'
                            WHEN task_run_id IS NOT NULL THEN 'leased'
                            ELSE 'available'
                        END
                        WHERE status IS NULL
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        UPDATE sandbox_sessions
                        SET workspace_dir = '/tmp/legacy-sandbox-' || SUBSTRING(container_id, 1, 12)
                        WHERE workspace_dir IS NULL
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        UPDATE sandbox_sessions
                        SET reuse_count = 0
                        WHERE reuse_count IS NULL
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS sandbox_sessions
                        ALTER COLUMN status SET DEFAULT 'available'
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS sandbox_sessions
                        ALTER COLUMN status SET NOT NULL
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS sandbox_sessions
                        ALTER COLUMN workspace_dir SET NOT NULL
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS sandbox_sessions
                        ALTER COLUMN reuse_count SET DEFAULT 0
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE IF EXISTS sandbox_sessions
                        ALTER COLUMN reuse_count SET NOT NULL
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS ix_sandbox_sessions_status
                        ON sandbox_sessions (status)
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS ix_sandbox_sessions_last_used_at
                        ON sandbox_sessions (last_used_at)
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        CREATE UNIQUE INDEX IF NOT EXISTS ux_sandbox_sessions_container_id
                        ON sandbox_sessions (container_id)
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
