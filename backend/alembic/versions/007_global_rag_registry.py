"""Add global RAG registry and project/task bindings.

Revision ID: 007_global_rag_registry
Revises: 006_task_queue_fields
Create Date: 2026-03-20 22:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "007_global_rag_registry"
down_revision = "006_task_queue_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    rag_file_status_enum = postgresql.ENUM(
        "PENDING",
        "RUNNING",
        "COMPLETED",
        "FAILED",
        name="ragfilestatus",
        create_type=False,
    )
    rag_file_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "rag_collections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_rag_collections_name"),
    )
    op.create_index("ix_rag_collections_name", "rag_collections", ["name"], unique=True)

    op.create_table(
        "rag_collection_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rag_collection_id", sa.Uuid(), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("status", rag_file_status_enum, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rag_collection_id"], ["rag_collections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rag_collection_files_rag_collection_id",
        "rag_collection_files",
        ["rag_collection_id"],
        unique=False,
    )

    op.add_column("projects", sa.Column("active_rag_collection_id", sa.Uuid(), nullable=True))
    op.create_index(
        "ix_projects_active_rag_collection_id",
        "projects",
        ["active_rag_collection_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_projects_active_rag_collection_id",
        "projects",
        "rag_collections",
        ["active_rag_collection_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("tasks", sa.Column("rag_collection_id", sa.Uuid(), nullable=True))
    op.create_index("ix_tasks_rag_collection_id", "tasks", ["rag_collection_id"], unique=False)
    op.create_foreign_key(
        "fk_tasks_rag_collection_id",
        "tasks",
        "rag_collections",
        ["rag_collection_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("document_chunk", sa.Column("rag_collection_id", sa.Uuid(), nullable=True))
    op.create_index(
        "ix_document_chunk_rag_collection_id",
        "document_chunk",
        ["rag_collection_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_document_chunk_rag_collection_id",
        "document_chunk",
        "rag_collections",
        ["rag_collection_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column("document_chunk", "project_id", existing_type=sa.Uuid(), nullable=True)

    op.add_column("document_index_jobs", sa.Column("rag_collection_id", sa.Uuid(), nullable=True))
    op.create_index(
        "ix_document_index_jobs_rag_collection_id",
        "document_index_jobs",
        ["rag_collection_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_document_index_jobs_rag_collection_id",
        "document_index_jobs",
        "rag_collections",
        ["rag_collection_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column("document_index_jobs", "project_id", existing_type=sa.Uuid(), nullable=True)
    op.alter_column("document_index_jobs", "project_node_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    op.alter_column("document_index_jobs", "project_node_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column("document_index_jobs", "project_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_constraint("fk_document_index_jobs_rag_collection_id", "document_index_jobs", type_="foreignkey")
    op.drop_index("ix_document_index_jobs_rag_collection_id", table_name="document_index_jobs")
    op.drop_column("document_index_jobs", "rag_collection_id")

    op.alter_column("document_chunk", "project_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_constraint("fk_document_chunk_rag_collection_id", "document_chunk", type_="foreignkey")
    op.drop_index("ix_document_chunk_rag_collection_id", table_name="document_chunk")
    op.drop_column("document_chunk", "rag_collection_id")

    op.drop_constraint("fk_tasks_rag_collection_id", "tasks", type_="foreignkey")
    op.drop_index("ix_tasks_rag_collection_id", table_name="tasks")
    op.drop_column("tasks", "rag_collection_id")

    op.drop_constraint("fk_projects_active_rag_collection_id", "projects", type_="foreignkey")
    op.drop_index("ix_projects_active_rag_collection_id", table_name="projects")
    op.drop_column("projects", "active_rag_collection_id")

    op.drop_index("ix_rag_collection_files_rag_collection_id", table_name="rag_collection_files")
    op.drop_table("rag_collection_files")

    op.drop_index("ix_rag_collections_name", table_name="rag_collections")
    op.drop_table("rag_collections")

    sa.Enum(
        "PENDING",
        "RUNNING",
        "COMPLETED",
        "FAILED",
        name="ragfilestatus",
    ).drop(op.get_bind(), checkfirst=True)
