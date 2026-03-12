"""enable pgvector extension

Revision ID: 001_pgvector
Revises:
Create Date: 2026-03-11

"""
from alembic import op

revision = '001_pgvector'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')


def downgrade():
    op.execute('DROP EXTENSION IF EXISTS vector')
