"""merge anak_batita and image_url migrations

Revision ID: 4680d486c883
Revises: 07db8eaa2137, 5ab3337ac828
Create Date: 2026-01-08 12:33:49.945859

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4680d486c883'
down_revision = ('07db8eaa2137', '5ab3337ac828')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
