"""Make RAG collections user-owned.

Revision ID: 009_rag_owner_user
Revises: 008_auth_user_owner
Create Date: 2026-03-20 23:55:00.000000
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa


revision = "009_rag_owner_user"
down_revision = "008_auth_user_owner"
branch_labels = None
depends_on = None

SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _has_column(bind: sa.engine.Connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(bind: sa.engine.Connection, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _has_unique_constraint(bind: sa.engine.Connection, table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(
        constraint["name"] == constraint_name
        for constraint in inspector.get_unique_constraints(table_name)
    )


def _has_fk(bind: sa.engine.Connection, table_name: str, fk_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(fk["name"] == fk_name for fk in inspector.get_foreign_keys(table_name))


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "rag_collections", "owner_user_id"):
        op.add_column("rag_collections", sa.Column("owner_user_id", sa.Uuid(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE rag_collections
            SET owner_user_id = :owner_user_id
            WHERE owner_user_id IS NULL
            """
        ).bindparams(owner_user_id=SYSTEM_USER_ID)
    )

    if not _has_index(bind, "rag_collections", "ix_rag_collections_owner_user_id"):
        op.create_index(
            "ix_rag_collections_owner_user_id",
            "rag_collections",
            ["owner_user_id"],
            unique=False,
        )

    if not _has_fk(bind, "rag_collections", "fk_rag_collections_owner_user_id"):
        op.create_foreign_key(
            "fk_rag_collections_owner_user_id",
            "rag_collections",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    if _has_index(bind, "rag_collections", "ix_rag_collections_name"):
        op.drop_index("ix_rag_collections_name", table_name="rag_collections")

    if _has_unique_constraint(bind, "rag_collections", "uq_rag_collections_name"):
        op.drop_constraint("uq_rag_collections_name", "rag_collections", type_="unique")

    if not _has_unique_constraint(bind, "rag_collections", "uq_rag_collections_owner_name"):
        op.create_unique_constraint(
            "uq_rag_collections_owner_name",
            "rag_collections",
            ["owner_user_id", "name"],
        )

    if not _has_index(bind, "rag_collections", "ix_rag_collections_name"):
        op.create_index("ix_rag_collections_name", "rag_collections", ["name"], unique=False)

    op.alter_column("rag_collections", "owner_user_id", existing_type=sa.Uuid(), nullable=False)


def downgrade() -> None:
    bind = op.get_bind()

    if _has_unique_constraint(bind, "rag_collections", "uq_rag_collections_owner_name"):
        op.drop_constraint("uq_rag_collections_owner_name", "rag_collections", type_="unique")

    if _has_index(bind, "rag_collections", "ix_rag_collections_name"):
        op.drop_index("ix_rag_collections_name", table_name="rag_collections")

    if not _has_unique_constraint(bind, "rag_collections", "uq_rag_collections_name"):
        op.create_unique_constraint("uq_rag_collections_name", "rag_collections", ["name"])

    if not _has_index(bind, "rag_collections", "ix_rag_collections_name"):
        op.create_index("ix_rag_collections_name", "rag_collections", ["name"], unique=True)

    if _has_fk(bind, "rag_collections", "fk_rag_collections_owner_user_id"):
        op.drop_constraint("fk_rag_collections_owner_user_id", "rag_collections", type_="foreignkey")

    if _has_index(bind, "rag_collections", "ix_rag_collections_owner_user_id"):
        op.drop_index("ix_rag_collections_owner_user_id", table_name="rag_collections")

    if _has_column(bind, "rag_collections", "owner_user_id"):
        op.drop_column("rag_collections", "owner_user_id")
