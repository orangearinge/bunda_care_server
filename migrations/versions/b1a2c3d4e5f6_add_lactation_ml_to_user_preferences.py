"""add lactation_ml to user_preferences

Revision ID: b1a2c3d4e5f6
Revises: 10a60ac40e5c
Create Date: 2025-11-08 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1a2c3d4e5f6'
down_revision = '10a60ac40e5c'
branch_labels = None
depends_on = None


def upgrade():
    try:
        op.add_column('user_preferences', sa.Column('lactation_ml', sa.Integer(), nullable=True))
    except Exception:
        pass


def downgrade():
    try:
        op.drop_column('user_preferences', 'lactation_ml')
    except Exception:
        pass
