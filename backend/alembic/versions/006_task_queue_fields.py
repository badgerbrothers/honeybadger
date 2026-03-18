"""Add task queue management fields.

Revision ID: 006_task_queue_fields
Revises: 1005_document_index_jobs
Create Date: 2026-03-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "006_task_queue_fields"
down_revision = "1005_document_index_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    queue_status_enum = sa.Enum("SCHEDULED", "QUEUED", "IN_PROGRESS", "DONE", name="queuestatus")
    queue_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "tasks",
        sa.Column(
            "queue_status",
            queue_status_enum,
            nullable=False,
            server_default="SCHEDULED",
        ),
    )
    op.add_column("tasks", sa.Column("scheduled_at", sa.DateTime(), nullable=True))
    op.add_column("tasks", sa.Column("priority", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("tasks", sa.Column("assigned_agent", sa.String(length=100), nullable=True))
    op.create_index("ix_tasks_queue_status", "tasks", ["queue_status"], unique=False)
    op.create_index("ix_tasks_scheduled_at", "tasks", ["scheduled_at"], unique=False)
    op.create_index("ix_tasks_priority", "tasks", ["priority"], unique=False)

    op.alter_column("tasks", "queue_status", server_default=None)
    op.alter_column("tasks", "priority", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_tasks_priority", table_name="tasks")
    op.drop_index("ix_tasks_scheduled_at", table_name="tasks")
    op.drop_index("ix_tasks_queue_status", table_name="tasks")
    op.drop_column("tasks", "assigned_agent")
    op.drop_column("tasks", "priority")
    op.drop_column("tasks", "scheduled_at")
    op.drop_column("tasks", "queue_status")
    sa.Enum("SCHEDULED", "QUEUED", "IN_PROGRESS", "DONE", name="queuestatus").drop(
        op.get_bind(),
        checkfirst=True,
    )
