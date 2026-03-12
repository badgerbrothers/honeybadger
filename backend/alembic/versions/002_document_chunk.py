"""add document_chunk table

Revision ID: 002_document_chunk
Revises: 001_pgvector
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = '002_document_chunk'
down_revision = '001_pgvector'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'document_chunk',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('chunk_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_document_chunk_project_id', 'document_chunk', ['project_id'])


def downgrade():
    op.drop_index('ix_document_chunk_project_id', 'document_chunk')
    op.drop_table('document_chunk')
