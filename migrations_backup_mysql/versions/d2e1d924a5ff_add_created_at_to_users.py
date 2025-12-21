"""add created_at to users

Revision ID: d2e1d924a5ff
Revises: e1f2a3b4c5d6
Create Date: 2025-11-24 19:56:50.762544

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2e1d924a5ff'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('created_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('users', 'created_at')
