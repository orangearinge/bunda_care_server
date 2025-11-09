"""rename dietary_restrictions to food_prohibitions on user_preferences

Revision ID: e1f2a3b4c5d6
Revises: da151179fdf0
Create Date: 2025-11-09 13:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'da151179fdf0'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if insp.has_table('user_preferences'):
        cols = {c['name'] for c in insp.get_columns('user_preferences')}
        try:
            if 'dietary_restrictions' in cols and 'food_prohibitions' not in cols:
                op.alter_column(
                    'user_preferences',
                    'dietary_restrictions',
                    new_column_name='food_prohibitions',
                    existing_type=sa.JSON(),
                )
        except Exception:
            pass


def downgrade():
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if insp.has_table('user_preferences'):
        cols = {c['name'] for c in insp.get_columns('user_preferences')}
        try:
            if 'food_prohibitions' in cols and 'dietary_restrictions' not in cols:
                op.alter_column(
                    'user_preferences',
                    'food_prohibitions',
                    new_column_name='dietary_restrictions',
                    existing_type=sa.JSON(),
                )
        except Exception:
            pass
