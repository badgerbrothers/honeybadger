"""Add document index jobs and convert document chunk project_id to UUID

Revision ID: 1005_document_index_jobs
Revises: 1004c8374fe5
Create Date: 2026-03-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "1005_document_index_jobs"
down_revision = "1004c8374fe5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_index_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("project_node_id", sa.Uuid(), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED", name="documentindexstatus"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_node_id"], ["project_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.alter_column(
        "document_chunk",
        "project_id",
        existing_type=sa.String(length=255),
        type_=sa.Uuid(),
        existing_nullable=False,
        postgresql_using="project_id::uuid",
    )
    op.create_foreign_key(
        "fk_document_chunk_project",
        "document_chunk",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_document_chunk_project", "document_chunk", type_="foreignkey")
    op.alter_column(
        "document_chunk",
        "project_id",
        existing_type=sa.Uuid(),
        type_=sa.String(length=255),
        existing_nullable=False,
        postgresql_using="project_id::text",
    )
    op.drop_table("document_index_jobs")
