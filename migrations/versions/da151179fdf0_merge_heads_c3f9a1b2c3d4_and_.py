"""merge heads cleanup for 2f3cd2b9a4d1

Revision ID: da151179fdf0
Revises: 2f3cd2b9a4d1
Create Date: 2025-11-09 12:59:02.095763

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'da151179fdf0'
down_revision = '2f3cd2b9a4d1'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # Only apply if food_logs table exists (it may have been dropped on another branch)
    if insp.has_table('food_logs'):
        cols = {c['name'] for c in insp.get_columns('food_logs')}
        if 'source_menu_id' not in cols:
            op.add_column('food_logs', sa.Column('source_menu_id', sa.Integer(), nullable=True))

        # Create FK if missing
        existing_fk_names = {fk['name'] for fk in insp.get_foreign_keys('food_logs') if fk.get('name')}
        if 'fk_food_logs_source_menu' not in existing_fk_names:
            op.create_foreign_key(
                'fk_food_logs_source_menu',
                'food_logs',
                'food_menus',
                ['source_menu_id'],
                ['id'],
                ondelete='SET NULL'
            )


def downgrade():
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if insp.has_table('food_logs'):
        # Drop FK if it exists
        try:
            op.drop_constraint('fk_food_logs_source_menu', 'food_logs', type_='foreignkey')
        except Exception:
            pass
        # Drop column if it exists
        cols = {c['name'] for c in insp.get_columns('food_logs')}
        if 'source_menu_id' in cols:
            try:
                op.drop_column('food_logs', 'source_menu_id')
            except Exception:
                pass
