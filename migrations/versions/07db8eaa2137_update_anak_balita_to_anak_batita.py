"""Update ANAK_BALITA to ANAK_BATITA role

Revision ID: 07db8eaa2137
Revises: f3e4fbb3d30f
Create Date: 2026-01-08 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '07db8eaa2137'
down_revision = 'f3e4fbb3d30f'
branch_labels = None
depends_on = None


def upgrade():
    # Update existing ANAK_BALITA role to ANAK_BATITA
    op.execute("UPDATE roles SET name = 'ANAK_BATITA', description = 'Infant 0-24 months' WHERE name = 'ANAK_BALITA'")
    
    # Update user preferences with the new role name
    op.execute("UPDATE user_preferences SET role = 'ANAK_BATITA' WHERE role = 'ANAK_BALITA'")


def downgrade():
    # Revert back to ANAK_BALITA
    op.execute("UPDATE roles SET name = 'ANAK_BALITA', description = 'Toddler child' WHERE name = 'ANAK_BATITA'")
    op.execute("UPDATE user_preferences SET role = 'ANAK_BALITA' WHERE role = 'ANAK_BATITA'")