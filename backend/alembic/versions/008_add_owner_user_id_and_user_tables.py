"""Add users/auth tables and project ownership column.

Revision ID: 008_auth_user_owner
Revises: 007_global_rag_registry
Create Date: 2026-03-20 23:10:00.000000
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa


revision = "008_auth_user_owner"
down_revision = "007_global_rag_registry"
branch_labels = None
depends_on = None

SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SYSTEM_USER_EMAIL = "system@badgers.local"
SYSTEM_PASSWORD_HASH = "system-user-not-for-login"


def _has_table(bind: sa.engine.Connection, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_column(bind: sa.engine.Connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(bind: sa.engine.Connection, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _has_fk(bind: sa.engine.Connection, table_name: str, fk_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(fk["name"] == fk_name for fk in inspector.get_foreign_keys(table_name))


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email", name="uq_users_email"),
        )

    if not _has_table(bind, "refresh_token_sessions"):
        op.create_table(
            "refresh_token_sessions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("token_hash", sa.String(length=128), nullable=False),
            sa.Column("issued_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("replaced_by_session_id", sa.Uuid(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["replaced_by_session_id"],
                ["refresh_token_sessions.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash", name="uq_refresh_token_sessions_token_hash"),
        )

    if not _has_index(bind, "refresh_token_sessions", "ix_refresh_token_sessions_user_id"):
        op.create_index(
            "ix_refresh_token_sessions_user_id",
            "refresh_token_sessions",
            ["user_id"],
            unique=False,
        )

    if not _has_index(bind, "refresh_token_sessions", "ix_refresh_token_sessions_expires_at"):
        op.create_index(
            "ix_refresh_token_sessions_expires_at",
            "refresh_token_sessions",
            ["expires_at"],
            unique=False,
        )

    op.execute(
        sa.text(
            """
            INSERT INTO users (id, email, password_hash)
            VALUES (:id, :email, :password_hash)
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(
            id=SYSTEM_USER_ID,
            email=SYSTEM_USER_EMAIL,
            password_hash=SYSTEM_PASSWORD_HASH,
        )
    )

    if not _has_column(bind, "projects", "owner_user_id"):
        op.add_column("projects", sa.Column("owner_user_id", sa.Uuid(), nullable=True))

    op.execute(
        sa.text(
            "UPDATE projects SET owner_user_id = :owner_user_id WHERE owner_user_id IS NULL"
        ).bindparams(owner_user_id=SYSTEM_USER_ID)
    )

    if not _has_index(bind, "projects", "ix_projects_owner_user_id"):
        op.create_index(
            "ix_projects_owner_user_id",
            "projects",
            ["owner_user_id"],
            unique=False,
        )

    if not _has_fk(bind, "projects", "fk_projects_owner_user_id"):
        op.create_foreign_key(
            "fk_projects_owner_user_id",
            "projects",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.alter_column("projects", "owner_user_id", existing_type=sa.Uuid(), nullable=False)


def downgrade() -> None:
    bind = op.get_bind()

    if _has_fk(bind, "projects", "fk_projects_owner_user_id"):
        op.drop_constraint("fk_projects_owner_user_id", "projects", type_="foreignkey")
    if _has_index(bind, "projects", "ix_projects_owner_user_id"):
        op.drop_index("ix_projects_owner_user_id", table_name="projects")
    if _has_column(bind, "projects", "owner_user_id"):
        op.drop_column("projects", "owner_user_id")

    if _has_index(bind, "refresh_token_sessions", "ix_refresh_token_sessions_expires_at"):
        op.drop_index("ix_refresh_token_sessions_expires_at", table_name="refresh_token_sessions")
    if _has_index(bind, "refresh_token_sessions", "ix_refresh_token_sessions_user_id"):
        op.drop_index("ix_refresh_token_sessions_user_id", table_name="refresh_token_sessions")
    if _has_table(bind, "refresh_token_sessions"):
        op.drop_table("refresh_token_sessions")

    if _has_table(bind, "users"):
        op.drop_table("users")
