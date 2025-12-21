"""Add google_id and avatar

Revision ID: 001828ee36e6
Revises: d2e1d924a5ff
Create Date: 2025-12-04 14:14:16.265550

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001828ee36e6'
down_revision = 'd2e1d924a5ff'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('google_id', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('avatar', sa.String(length=255), nullable=True))
    op.create_unique_constraint('uq_users_google_id', 'users', ['google_id'])


def downgrade():
    op.drop_constraint('uq_users_google_id', 'users', type_='unique')
    op.drop_column('users', 'avatar')
    op.drop_column('users', 'google_id')
