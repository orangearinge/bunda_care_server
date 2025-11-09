"""drop food_label_map

Revision ID: 2f3cd2b9a4d1
Revises: 1907cb40d747
Create Date: 2025-11-09 02:38:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2f3cd2b9a4d1'
down_revision = '1907cb40d747'
branch_labels = None
depends_on = None


def upgrade():
    # Drop index if exists, then drop table
    try:
        op.drop_index('ix_food_label_map_label', table_name='food_label_map')
    except Exception:
        pass
    try:
        op.drop_table('food_label_map')
    except Exception:
        pass


def downgrade():
    # Recreate the table and index to reverse the drop
    op.create_table(
        'food_label_map',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('label', sa.String(length=150), nullable=False),
        sa.Column('normalized_label', sa.String(length=150), nullable=True),
        sa.Column('ingredient_id', sa.Integer(), sa.ForeignKey('food_ingredients.id', ondelete='CASCADE'), nullable=False),
    )
    op.create_index('ix_food_label_map_label', 'food_label_map', ['label'], unique=True)
