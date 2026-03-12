"""Add memory system tables

Revision ID: 003_memory_system
Revises: 1004c8374fe5
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = '003_memory_system'
down_revision = '002_document_chunk'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('conversation_summaries',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('conversation_id', sa.Uuid(), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=False),
        sa.Column('message_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversation_summaries_conversation_id', 'conversation_summaries', ['conversation_id'])

    op.create_table('project_memories',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('memory_type', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('memory_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_project_memories_project_id', 'project_memories', ['project_id'])
    op.execute('CREATE INDEX ix_project_memories_embedding ON project_memories USING ivfflat (embedding vector_cosine_ops)')


def downgrade() -> None:
    op.drop_index('ix_project_memories_embedding', table_name='project_memories')
    op.drop_index('ix_project_memories_project_id', table_name='project_memories')
    op.drop_table('project_memories')
    op.drop_index('ix_conversation_summaries_conversation_id', table_name='conversation_summaries')
    op.drop_table('conversation_summaries')
